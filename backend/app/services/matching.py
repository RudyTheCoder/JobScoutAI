from __future__ import annotations

from difflib import SequenceMatcher

from app import models


def score_job(job: models.Job, settings: models.UserSettings | None) -> tuple[float, dict]:
    if not settings:
        return 0, {"reason": "No preferences or resume text configured."}

    required = {item.lower() for item in settings.required_skills}
    job_skills = {item.lower() for item in (job.skills or [])}
    skill_score = (len(required & job_skills) / len(required) * 50) if required else 25

    title_score = 0.0
    for target in settings.target_titles:
        title_score = max(title_score, SequenceMatcher(None, target.lower(), job.title.lower()).ratio() * 20)

    location_text = (job.location or "").lower()
    preferred_locations = [item.lower() for item in settings.preferred_locations]
    location_match = any(item in location_text for item in preferred_locations) if preferred_locations else False
    arrangement_match = settings.work_arrangement == "any" or settings.work_arrangement == (job.work_arrangement or "")
    location_score = 15 if location_match or arrangement_match else 0

    experience_score = 10 if settings.experience_level == (job.experience_level or "") else 0
    salary_score = 0
    if settings.minimum_salary is None:
        salary_score = 5
    elif job.salary_max and job.salary_max >= settings.minimum_salary:
        salary_score = 5

    score = min(100, round(skill_score + title_score + location_score + experience_score + salary_score))
    return score, {
        "matching_skills": sorted(required & job_skills),
        "missing_skills": sorted(required - job_skills),
        "location_match": location_match,
        "work_arrangement_match": arrangement_match,
        "experience_match": experience_score > 0,
        "salary_match": salary_score > 0,
    }
