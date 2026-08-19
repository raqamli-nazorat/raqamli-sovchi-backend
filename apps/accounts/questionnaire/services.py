from apps.accounts.questionnaire.models import UserAnswer


def get_effective_candidate_role(profile):
    """
    Profilning amaldagi nomzodlik rolini (kuyov / kelin) aniqlaydi.

    :param profile: Profil obyekti (Profile).
    :return: "groom", "bride" yoki None (string | None).
    """
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
    """
    Ikkita profil (foydalanuvchi anketalari) o'rtasidagi so'rovnoma javoblariga asoslangan
    moslik foizini (compatibility score) va bo'limlar bo'yicha ballarni hisoblaydi.

    :param source_profile: Asosiy (izlayotgan) profil.
    :param target_profile: Nishon (solishtirilayotgan) profil.
    :return: {"overall_score": float, "sections": list} yoki None.
    """
    if not source_profile or not target_profile:
        return None

    if source_profile.id == target_profile.id:
        return {
            "overall_score": 100.0,
            "sections": [],
        }

    source_answers_qs = UserAnswer.objects.filter(
        profile=source_profile
    ).select_related("selected_option", "question", "question__section")

    source_answers = {}
    for ans in source_answers_qs:
        sec = ans.question.section
        q_key = (sec.id, ans.question.order) if sec else ans.question.order
        source_answers[q_key] = {
            "weight": ans.selected_option.weight,
            "section_id": sec.id if sec else None,
            "section_name": sec.name if sec else "Umumiy",
        }

    if not source_answers:
        return None

    target_answers_qs = UserAnswer.objects.filter(
        profile=target_profile
    ).select_related("selected_option", "question", "question__section")

    target_answers = {}
    for ans in target_answers_qs:
        sec = ans.question.section
        q_key = (sec.id, ans.question.order) if sec else ans.question.order
        target_answers[q_key] = {
            "weight": ans.selected_option.weight,
            "section_id": sec.id if sec else None,
            "section_name": sec.name if sec else "Umumiy",
        }

    if not target_answers:
        return None

    common_qids = set(source_answers.keys()) & set(target_answers.keys())
    if not common_qids:
        return None

    total_score = 0
    total_max = 0
    section_stats = {}

    for qid in common_qids:
        w_a = source_answers[qid]["weight"]
        w_b = target_answers[qid]["weight"]
        sec_name = source_answers[qid]["section_name"]
        sec_id = source_answers[qid]["section_id"]

        diff = abs(w_a - w_b)
        q_score = max(0, 10 - diff)

        total_score += q_score
        total_max += 10

        if sec_name not in section_stats:
            section_stats[sec_name] = {
                "section_id": str(sec_id) if sec_id else None,
                "score": 0,
                "max": 0,
            }
        section_stats[sec_name]["score"] += q_score
        section_stats[sec_name]["max"] += 10

    if total_max == 0:
        return None

    overall_score = round((total_score / total_max) * 100.0, 1)

    sections_list = []
    for sec_name, stats in section_stats.items():
        if stats["max"] > 0:
            sec_score = round((stats["score"] / stats["max"]) * 100.0, 1)
            sections_list.append(
                {
                    "section_id": stats["section_id"],
                    "section_name": sec_name,
                    "score": sec_score,
                }
            )

    return {
        "overall_score": overall_score,
        "sections": sections_list,
    }


def batch_calculate_compatibility_scores(source_profile, target_profiles):
    """
    Bir nechta nomzod anketalari (target_profiles) uchun moslik ballarini ommaviy (batch) tartibda optimizeshgan holda hisoblaydi.

    :param source_profile: Asosiy (izlayotgan) profil.
    :param target_profiles: Solishtirilishi kerak bo'lgan profillar ro'yxati yoki QuerySet.
    :return: {profile_id: {"overall_score": float, "sections": list} | None} lug'ati.
    """
    if not source_profile or not target_profiles:
        return {}

    source_answers_qs = UserAnswer.objects.filter(
        profile=source_profile
    ).select_related("selected_option", "question", "question__section")

    source_answers = {}
    for ans in source_answers_qs:
        sec = ans.question.section
        q_key = (sec.id, ans.question.order) if sec else ans.question.order
        source_answers[q_key] = {
            "weight": ans.selected_option.weight,
            "section_id": sec.id if sec else None,
            "section_name": sec.name if sec else "Umumiy",
        }

    if not source_answers:
        return {p.id: None for p in target_profiles}

    target_ids = [p.id for p in target_profiles]

    target_answers_qs = UserAnswer.objects.filter(
        profile_id__in=target_ids
    ).select_related("selected_option", "question", "question__section")

    target_answers_map = {}
    for ans in target_answers_qs:
        if ans.profile_id not in target_answers_map:
            target_answers_map[ans.profile_id] = {}
        sec = ans.question.section
        q_key = (sec.id, ans.question.order) if sec else ans.question.order
        target_answers_map[ans.profile_id][q_key] = {
            "weight": ans.selected_option.weight,
            "section_id": sec.id if sec else None,
            "section_name": sec.name if sec else "Umumiy",
        }

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
        section_stats = {}

        for qid in common_ids:
            w_a = source_answers[qid]["weight"]
            w_b = p_answers[qid]["weight"]
            sec_name = source_answers[qid]["section_name"]
            sec_id = source_answers[qid]["section_id"]

            diff = abs(w_a - w_b)
            q_score = max(0, 10 - diff)

            total_score += q_score
            total_max += 10

            if sec_name not in section_stats:
                section_stats[sec_name] = {
                    "section_id": str(sec_id) if sec_id else None,
                    "score": 0,
                    "max": 0,
                }
            section_stats[sec_name]["score"] += q_score
            section_stats[sec_name]["max"] += 10

        if total_max > 0:
            overall_score = round((total_score / total_max) * 100.0, 1)
            sections_list = []
            for sec_name, stats in section_stats.items():
                if stats["max"] > 0:
                    sec_score = round((stats["score"] / stats["max"]) * 100.0, 1)
                    sections_list.append(
                        {
                            "section_id": stats["section_id"],
                            "section_name": sec_name,
                            "score": sec_score,
                        }
                    )
            scores[p.id] = {
                "overall_score": overall_score,
                "sections": sections_list,
            }
        else:
            scores[p.id] = None

    return scores


def bulk_save_question_options(question_id, options_data):
    """
    Savol variantsiyalarini (QuestionOption) ommaviy tarzda yaratadi yoki yangilaydi.

    :param question_id: Tegishli savol ID si.
    :param options_data: Variantlar ma'lumotlari ro'yxati (list of dicts).
    :return: (yaratilganlar_soni, yangilanganlar_soni) juftligi (tuple).
    """
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
    """
    Foydalanuvchining so'rovnomadagi javoblarini ommaviy yaratadi yoki yangilaydi.

    :param profile_id: Foydalanuvchi profili ID si.
    :param answers_data: Savol va tanlangan variantlar ma'lumotlari ro'yxati.
    :return: Saqlangan javoblar soni (int).
    """
    created_answers = []
    for item in answers_data:
        ans, _ = UserAnswer.objects.update_or_create(
            profile_id=profile_id,
            question_id=item["question_id"],
            defaults={"selected_option_id": item["selected_option_id"]},
        )
        created_answers.append(ans)
    return len(created_answers)
