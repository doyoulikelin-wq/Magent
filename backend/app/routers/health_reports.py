"""Health reports router – parses Liver subject XLS exam data from disk."""

import logging
import re
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter()

_LIVER_DIR = Path(__file__).resolve().parents[3] / "fatty_liver_data_raw"


# ── Helpers ──────────────────────────────────────────────────


def _find_subject_folder(base_dir: Path, subject_id: str) -> Path | None:
    """Find the folder whose name starts with the subject_id (e.g. Liver-001)."""
    if not base_dir.is_dir():
        return None
    for p in base_dir.iterdir():
        if p.is_dir() and p.name.startswith(subject_id):
            return p
    return None


def _find_xls_in_folder(folder: Path) -> Path | None:
    """Return the first .xls/.xlsx file in the given folder."""
    for ext in ("*.xls", "*.xlsx"):
        files = list(folder.glob(ext))
        if files:
            return files[0]
    return None


def _parse_exam_xls(path: Path) -> dict[str, Any]:
    """Parse a Liver exam XLS file.

    Structure:
      Row 0-1: empty
      Row 2:   header_labels (病人姓名, 年龄, 性别, 登记号, 审核时间, 医嘱名称, 项目名称, 结果, [异常提示], 单位, 参考范围, ...)
      Row 3+:  data rows
        - Rows where col0 is not NaN: patient info row (name, age, sex, id, audit_time) + first test item
        - Rows where col0 is NaN: continuation test items

    Returns a dict with patient info and list of lab items.
    """
    df = pd.read_excel(path, header=None)

    if len(df) < 3:
        return {"items": [], "patient": {}, "audit_dates": []}

    # Row 2 is the header row — build a column-name map
    headers = [str(df.iloc[2, c]).strip() if pd.notna(df.iloc[2, c]) else "" for c in range(df.shape[1])]

    # Build column index lookup
    col_map: dict[str, int] = {}
    for i, h in enumerate(headers):
        if h and h not in col_map:
            col_map[h] = i

    # Required columns
    name_col = col_map.get("项目名称")
    result_col = col_map.get("结果")
    unit_col = col_map.get("单位")
    ref_col = col_map.get("参考范围")
    abnormal_col = col_map.get("异常提示")  # may be None for 结束数据
    audit_col = col_map.get("审核时间")
    patient_name_col = col_map.get("病人姓名")
    age_col = col_map.get("年龄")
    sex_col = col_map.get("性别")
    order_col = col_map.get("医嘱名称")

    if name_col is None or result_col is None:
        logger.warning("XLS missing required columns 项目名称/结果: %s", path)
        return {"items": [], "patient": {}, "audit_dates": []}

    # Extract patient info from first data row (row 3)
    patient: dict[str, str] = {}
    if len(df) > 3 and patient_name_col is not None:
        p_name = df.iloc[3, patient_name_col]
        if pd.notna(p_name):
            patient["name"] = str(p_name).strip()
        if age_col is not None and pd.notna(df.iloc[3, age_col]):
            patient["age"] = str(df.iloc[3, age_col]).strip()
        if sex_col is not None and pd.notna(df.iloc[3, sex_col]):
            patient["sex"] = str(df.iloc[3, sex_col]).strip()

    # Extract all lab items and audit dates
    items: list[dict[str, str | None]] = []
    audit_dates: set[str] = set()
    current_order = ""
    current_audit = ""

    for i in range(3, len(df)):
        # Check if this is a patient-info row (group start)
        if patient_name_col is not None and pd.notna(df.iloc[i, patient_name_col]):
            if order_col is not None and pd.notna(df.iloc[i, order_col]):
                current_order = str(df.iloc[i, order_col]).strip()
            if audit_col is not None and pd.notna(df.iloc[i, audit_col]):
                raw_audit = str(df.iloc[i, audit_col]).strip()
                # Extract just the date part
                date_part = raw_audit[:10] if len(raw_audit) >= 10 else raw_audit
                current_audit = date_part
                audit_dates.add(date_part)

        # Extract test item if present
        test_name = df.iloc[i, name_col]
        if pd.notna(test_name) and str(test_name).strip() and str(test_name).strip() != "项目名称":
            item: dict[str, str | None] = {
                "name": str(test_name).strip(),
                "value": str(df.iloc[i, result_col]).strip() if pd.notna(df.iloc[i, result_col]) else None,
                "unit": str(df.iloc[i, unit_col]).strip() if unit_col is not None and pd.notna(df.iloc[i, unit_col]) else None,
                "reference": str(df.iloc[i, ref_col]).strip() if ref_col is not None and pd.notna(df.iloc[i, ref_col]) else None,
                "abnormal": str(df.iloc[i, abnormal_col]).strip() if abnormal_col is not None and pd.notna(df.iloc[i, abnormal_col]) else None,
                "order_name": current_order or None,
                "audit_date": current_audit or None,
            }
            items.append(item)

    return {
        "patient": patient,
        "items": items,
        "audit_dates": sorted(audit_dates),
    }


# ── Endpoint ──────────────────────────────────────────────────


@router.get("")
def get_health_reports(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return parsed health exam reports for the current (Liver) subject.

    Response:
    {
      "subject_id": "Liver-001",
      "cohort": "liver",
      "patient": {"name": "...", "age": "...", "sex": "..."},
      "phases": [
        {
          "phase": "初始",
          "date": "2025-11-01",
          "items": [ { "name": "谷丙转氨酶", "value": "28", "unit": "IU/L", "reference": "0-50", "abnormal": null } ]
        },
        {
          "phase": "结束",
          "date": "2026-01-22",
          ...
        }
      ]
    }
    """
    # Look up the subject for this user
    profile = db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).scalars().first()

    if not profile or not profile.subject_id:
        raise HTTPException(status_code=404, detail="No subject profile found")

    sid = profile.subject_id

    # Only Liver subjects have exam data
    if not sid.startswith("Liver"):
        return {
            "subject_id": sid,
            "cohort": profile.cohort,
            "patient": {},
            "phases": [],
        }

    phases: list[dict[str, Any]] = []
    patient: dict[str, str] = {}

    # Parse 初始数据
    init_folder = _find_subject_folder(_LIVER_DIR / "初始数据", sid)
    if init_folder:
        xls = _find_xls_in_folder(init_folder)
        if xls:
            parsed = _parse_exam_xls(xls)
            if not patient and parsed["patient"]:
                patient = parsed["patient"]
            phases.append({
                "phase": "初始",
                "label": "基线体检",
                "dates": parsed["audit_dates"],
                "items": parsed["items"],
            })

    # Parse 结束数据
    end_folder = _find_subject_folder(_LIVER_DIR / "结束数据", sid)
    if end_folder:
        xls = _find_xls_in_folder(end_folder)
        if xls:
            parsed = _parse_exam_xls(xls)
            if not patient and parsed["patient"]:
                patient = parsed["patient"]
            phases.append({
                "phase": "结束",
                "label": "结束体检",
                "dates": parsed["audit_dates"],
                "items": parsed["items"],
            })

    return {
        "subject_id": sid,
        "cohort": profile.cohort,
        "patient": patient,
        "phases": phases,
    }
