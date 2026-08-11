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


def bulk_save_question_options(question_id, options_data):
    from django.db import transaction
    from apps.accounts.questionnaire.models import QuestionOption

    existing_options = {
        opt.option_letter: opt
        for opt in QuestionOption.objects.filter(question_id=question_id)
    }
    existing_by_id = {str(opt.id): opt for opt in existing_options.values()}

    to_create = []
    to_update = []

    with transaction.atomic():
        for item in options_data:
            item_id = str(item.get("id")) if item.get("id") else None
            letter = item["option_letter"]
            text = item["text"]
            weight = item["weight"]

            target_opt = None
            if item_id and item_id in existing_by_id:
                target_opt = existing_by_id[item_id]
            elif letter in existing_options:
                target_opt = existing_options[letter]

            if target_opt:
                target_opt.option_letter = letter
                target_opt.text = text
                target_opt.weight = weight
                to_update.append(target_opt)
            else:
                new_opt = QuestionOption(
                    question_id=question_id,
                    option_letter=letter,
                    text=text,
                    weight=weight,
                )
                to_create.append(new_opt)

        created_count = 0
        updated_count = 0

        if to_create:
            QuestionOption.objects.bulk_create(to_create)
            created_count = len(to_create)

        if to_update:
            QuestionOption.objects.bulk_update(
                to_update, fields=["option_letter", "text", "weight"]
            )
            updated_count = len(to_update)

    return created_count, updated_count


def bulk_save_user_answers(profile_id, answers_data):
    created_answers = []
    for item in answers_data:
        ans, _ = UserAnswer.objects.update_or_create(
            profile_id=profile_id,
            question_id=item["question_id"],
            defaults={"selected_option_id": item["selected_option_id"]},
        )
        created_answers.append(ans)
    return len(created_answers)
