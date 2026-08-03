from django.db.models import Q


def is_female_candidate(profile):
    if not profile:
        return False

    if profile.gender == "female" or profile.candidate_type == "bride":
        return True

    if hasattr(profile, "representative_info") and profile.representative_info:
        if profile.representative_info.candidate_role == "bride":
            return True

    return False


def can_view_profile_photos(request_user, target_profile):
    if not request_user or not request_user.is_authenticated:
        return False

    if not target_profile:
        return False

    if target_profile.user_id == request_user.id:
        return True

    from apps.matches.match_requests.models import MatchRequest, MatchRequestStatus

    user_profile = getattr(request_user, "profile", None)

    has_accepted_match = False
    if user_profile:
        has_accepted_match = MatchRequest.objects.filter(
            status=MatchRequestStatus.ACCEPTED
        ).filter(
            (
                Q(from_profile=user_profile, to_profile=target_profile)
                | Q(from_profile=target_profile, to_profile=user_profile)
            )
        ).exists()

    if is_female_candidate(target_profile):
        return has_accepted_match

    if request_user.is_staff or request_user.is_superuser:
        return True

    if has_accepted_match:
        return True

    if not target_profile.blur_photos:
        return True

    return False
