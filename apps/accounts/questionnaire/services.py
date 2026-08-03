from apps.accounts.questionnaire.models import UserAnswer


def get_effective_candidate_role(profile):
    if not profile:
        return None

    if profile.candidate_type in ["groom", "bride"]:
        return profile.candidate_type

    if profile.gender == "male":
        return "groom"
    elif profile.gender == "female":
        return "bride"

    if hasattr(profile, "representative_info") and profile.representative_info:
        return profile.representative_info.candidate_role

    return None


def calculate_compatibility_score(source_profile, target_profile):
    if not source_profile or not target_profile:
        return None

    if source_profile.id == target_profile.id:
        return 100.0

    source_answers = {
        ans.question_id: ans.selected_option.weight
        for ans in UserAnswer.objects.filter(profile=source_profile).select_related(
            "selected_option"
        )
    }

    if not source_answers:
        return None

    target_answers = {
        ans.question_id: ans.selected_option.weight
        for ans in UserAnswer.objects.filter(profile=target_profile).select_related(
            "selected_option"
        )
    }

    if not target_answers:
        return None

    common_qids = set(source_answers.keys()) & set(target_answers.keys())
    if not common_qids:
        return None

    total_score = 0
    total_max = 0

    for qid in common_qids:
        w_a = source_answers[qid]
        w_b = target_answers[qid]
        diff = abs(w_a - w_b)
        total_score += max(0, 10 - diff)
        total_max += 10

    if total_max == 0:
        return None

    return round((total_score / total_max) * 100.0, 1)


def batch_calculate_compatibility_scores(source_profile, target_profiles):
    if not source_profile or not target_profiles:
        return {}

    source_answers = {
        ans.question_id: ans.selected_option.weight
        for ans in UserAnswer.objects.filter(profile=source_profile).select_related(
            "selected_option"
        )
    }

    if not source_answers:
        return {p.id: None for p in target_profiles}

    target_ids = [p.id for p in target_profiles]

    target_answers_qs = UserAnswer.objects.filter(
        profile_id__in=target_ids
    ).select_related("selected_option")

    target_answers_map = {}
    for ans in target_answers_qs:
        if ans.profile_id not in target_answers_map:
            target_answers_map[ans.profile_id] = {}
        target_answers_map[ans.profile_id][ans.question_id] = ans.selected_option.weight

    scores = {}
    for p in target_profiles:
        p_answers = target_answers_map.get(p.id, {})
        if not p_answers:
            scores[p.id] = None
            continue

        common_ids = set(source_answers.keys()) & set(p_answers.keys())
        if not common_ids:
            scores[p.id] = None
            continue

        total_score = 0
        total_max = 0
        for qid in common_ids:
            w_a = source_answers[qid]
            w_b = p_answers[qid]
            diff = abs(w_a - w_b)
            total_score += max(0, 10 - diff)
            total_max += 10

        if total_max > 0:
            scores[p.id] = round((total_score / total_max) * 100.0, 1)
        else:
            scores[p.id] = None

    return scores
