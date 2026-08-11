import logging
import os
import tempfile
import uuid
from contextlib import contextmanager
import math

from PIL import Image, ImageOps

try:
    from deepface import DeepFace

    DEEPFACE_AVAILABLE = True
except Exception:
    DeepFace = None
    DEEPFACE_AVAILABLE = False

logger = logging.getLogger("face_verification")

MODEL_NAME = "ArcFace"
DETECTOR_BACKEND = "retinaface"
MAX_DISTANCE = 0.45
REQUIRE_ANTISPOOFING = True


@contextmanager
def _temp_jpeg_files(*labels):
    request_id = uuid.uuid4().hex
    temp_dir = tempfile.gettempdir()
    paths = [os.path.join(temp_dir, f"{label}_{request_id}.jpg") for label in labels]
    try:
        yield paths
    finally:
        for p in paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                logger.warning("Vaqtinchalik faylni o'chirib bo'lmadi: %s", p)


def _save_as_rgb_jpeg(source, dest_path):
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image.load()
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(dest_path, format="JPEG", quality=95)


def _write_field_file_to_path(field_file, dest_path):
    field_file.open("rb")
    try:
        with open(dest_path, "wb") as f:
            f.write(field_file.read())
    finally:
        field_file.close()


def calculate_cosine_distance(v1, v2):
    if not v1 or not v2 or len(v1) != len(v2):
        return 1.0

    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))

    if norm_v1 == 0 or norm_v2 == 0:
        return 1.0

    similarity = dot_product / (norm_v1 * norm_v2)
    return float(1.0 - similarity)


def _check_liveness(image_path):
    try:
        faces = DeepFace.extract_faces(
            img_path=image_path,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
            anti_spoofing=True,
        )
    except ValueError as e:
        logger.warning("_check_liveness: yuz topilmadi: %s", e)
        return False, "no_face"

    if not faces:
        return False, "no_face"

    face = faces[0]
    is_real = face.get("is_real", False)
    score = face.get("antispoof_score")
    logger.debug("_check_liveness: is_real=%s score=%s", is_real, score)

    if not is_real:
        return False, f"spoof (score={score})"
    return True, "real"


def extract_embedding(image_path):
    if not DEEPFACE_AVAILABLE:
        return None

    try:
        results = DeepFace.represent(
            img_path=image_path,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
            anti_spoofing=False,
        )
        if results and isinstance(results, list) and "embedding" in results[0]:
            return results[0]["embedding"]
    except Exception as e:
        logger.warning("extract_embedding xatoligi: %s", e)
    return None


def verify_face_image(uploaded_file):
    if not DEEPFACE_AVAILABLE:
        logger.error("DeepFace o'rnatilmagan — profil rasmi rad etildi.")
        return (
            False,
            "Tekshiruv tizimi tayyor emas. Administratorga murojaat qiling.",
            None,
        )

    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    with _temp_jpeg_files("profile_upload") as (temp_path,):
        try:
            _save_as_rgb_jpeg(uploaded_file, temp_path)

            faces = DeepFace.extract_faces(
                img_path=temp_path,
                detector_backend=DETECTOR_BACKEND,
                enforce_detection=True,
                anti_spoofing=False,
            )

            if not faces:
                return (
                    False,
                    "Yuz aniqlanmadi. Iltimos, yuzingizni kameraga aniq ko'rsatib qayta urinib ko'ring.",
                    None,
                )

            if len(faces) > 1:
                return (
                    False,
                    "Kadrda bir nechta yuz aniqlandi. Faqat o'zingiz ko'rinishingiz kerak.",
                    None,
                )

            if REQUIRE_ANTISPOOFING:
                is_real, spoof_msg = _check_liveness(temp_path)
                if not is_real and spoof_msg != "no_face":
                    return (
                        False,
                        "Tiriklikni tasdiqlab bo'lmadi. Iltimos, yorug' joyda kameraga to'g'ri qarab qaytadan urinib ko'ring.",
                        None,
                    )

            embedding = extract_embedding(temp_path)
            return True, "Yuz muvaffaqiyatli aniqlandi.", embedding

        except ValueError:
            return (
                False,
                "Yuz aniqlanmadi. Iltimos, kameraga to'g'ri qarab qayta urinib ko'ring.",
                None,
            )
        except Exception as e:
            logger.exception("verify_face_image kutilmagan xatolik")
            return (
                False,
                "Tekshirishda xatolik yuz berdi. Qayta urinib ko'ring.",
                None,
            )


def hash_compare(profile_or_user, uploaded_file):
    if not DEEPFACE_AVAILABLE:
        logger.error("DeepFace o'rnatilmagan — yuz tekshiruvi rad etildi.")
        return False, "Tekshiruv tizimi tayyor emas. Administratorga murojaat qiling."

    profile = getattr(profile_or_user, "profile", profile_or_user)
    if not hasattr(profile, "photos"):
        return False, "Foydalanuvchi profili topilmadi."

    photos = list(profile.photos.filter(is_active=True).order_by("-is_main", "order"))
    if not photos:
        return False, "Profil rasmlari topilmadi. Avval profil rasmingizni yuklang."

    profile_id = getattr(profile, "id", "Unknown")
    user_id = getattr(profile, "user_id", "Unknown")

    with _temp_jpeg_files(f"probe_{profile_id}") as (probe_path,):
        try:
            try:
                uploaded_file.seek(0)
            except Exception:
                pass
            _save_as_rgb_jpeg(uploaded_file, probe_path)

            if REQUIRE_ANTISPOOFING:
                is_real, spoof_msg = _check_liveness(probe_path)
                if not is_real and spoof_msg != "no_face":
                    logger.info(
                        "Yuz tekshiruvi rad etildi (spoofing): ProfileID=%s | UserID=%s | Sabab=%s",
                        profile_id,
                        user_id,
                        spoof_msg,
                    )
                    return (
                        False,
                        "Tiriklikni tasdiqlab bo'lmadi. Iltimos, yorug' joyda kameraga to'g'ri qarab qaytadan urinib ko'ring.",
                    )

            try:
                faces = DeepFace.extract_faces(
                    img_path=probe_path,
                    detector_backend=DETECTOR_BACKEND,
                    enforce_detection=True,
                    anti_spoofing=False,
                )
                if not faces:
                    return (
                        False,
                        "Yuz aniqlanmadi. Iltimos, yuzingizni kameraga aniq ko'rsatib qayta urinib ko'ring.",
                    )
                if len(faces) > 1:
                    return (
                        False,
                        "Kadrda bir nechta yuz aniqlandi. Faqat o'zingiz ko'rinishingiz kerak.",
                    )
            except ValueError:
                return (
                    False,
                    "Yuz aniqlanmadi. Iltimos, yuzingizni kameraga aniq ko'rsatib qayta urinib ko'ring.",
                )
            except Exception as e:
                logger.warning("DeepFace extract_faces xatoligi: %s", e)

            probe_embedding = extract_embedding(probe_path)
            if not probe_embedding:
                return (
                    False,
                    "Yuz aniqlanmadi. Iltimos, kameraga to'g'ri qarab qayta urinib ko'ring.",
                )

            for photo in photos:
                if not photo.image or not photo.image.name:
                    continue

                photo_embedding = photo.embedding

                if not photo_embedding:
                    with _temp_jpeg_files(f"base_{photo.id}") as (base_path,):
                        try:
                            _write_field_file_to_path(photo.image, base_path)
                            photo_embedding = extract_embedding(base_path)
                            if photo_embedding:
                                photo.embedding = photo_embedding
                                photo.save(update_fields=["embedding", "updated_at"])
                        except Exception as e:
                            logger.warning(
                                "PhotoID=%s embedding olishda xatolik: %s", photo.id, e
                            )
                            continue

                if not photo_embedding:
                    continue

                distance = calculate_cosine_distance(probe_embedding, photo_embedding)
                if distance <= MAX_DISTANCE:
                    logger.info(
                        "Yuz tekshiruvi tasdiqlandi: ProfileID=%s | UserID=%s | PhotoID=%s | distance=%.4f",
                        profile_id,
                        user_id,
                        photo.id,
                        distance,
                    )
                    return True, "Yuz muvaffaqiyatli tasdiqlandi."

            logger.info(
                "Yuz tekshiruvi rad etildi (hech bir rasm mos kelmadi): ProfileID=%s | UserID=%s",
                profile_id,
                user_id,
            )
            return (
                False,
                "Yuz mos kelmadi. Yuklangan rasm profildagi rasmlaringizdan birortasiga ham to'g'ri kelmadi.",
            )

        except Exception as e:
            logger.exception(
                "hash_compare kutilmagan xatolik: ProfileID=%s | UserID=%s",
                profile_id,
                user_id,
            )
            return False, "Tekshiruvda xatolik yuz berdi. Qayta urinib ko'ring."


def check_against_blocked_faces(probe_embedding, strict_threshold=0.40):
    if not probe_embedding:
        return False, None, 1.0

    from apps.accounts.users.models import BlockedFace

    blocked_faces = list(BlockedFace.objects.filter(is_active=True))
    for bf in blocked_faces:
        if not bf.embedding:
            continue
        dist = calculate_cosine_distance(probe_embedding, bf.embedding)
        if dist <= strict_threshold:
            logger.warning(
                "Bloklangan yuz mosligi aniqlandi! BlockedFaceID=%s | UserID=%s | distance=%.4f",
                bf.id,
                bf.user_id,
                dist,
            )
            return True, bf, dist

    return False, None, 1.0


def register_user_faces_as_blocked(user, reason=None, embedding=None):
    if not user:
        return

    from apps.accounts.users.models import BlockedFace

    default_reason = (
        reason or "Foydalanuvchi bloklanganligi sababli yuzi qora ro'yxatga olindi."
    )

    if embedding:
        exists = BlockedFace.objects.filter(user=user, embedding=embedding).exists()
        if not exists:
            BlockedFace.objects.create(
                user=user,
                embedding=embedding,
                reason=default_reason,
            )

    profile = getattr(user, "profile", None)
    if not profile or not hasattr(profile, "photos"):
        return

    photos = profile.photos.filter(is_active=True)
    for photo in photos:
        emb = photo.embedding
        if not emb and photo.image and photo.image.name:
            with _temp_jpeg_files(f"block_{photo.id}") as (temp_path,):
                try:
                    _write_field_file_to_path(photo.image, temp_path)
                    emb = extract_embedding(temp_path)
                    if emb:
                        photo.embedding = emb
                        photo.save(update_fields=["embedding", "updated_at"])
                except Exception as e:
                    logger.warning(
                        "PhotoID=%s embedding olishda xatolik: %s", photo.id, e
                    )

        if emb:
            exists = BlockedFace.objects.filter(user=user, embedding=emb).exists()
            if not exists:
                BlockedFace.objects.create(
                    user=user,
                    embedding=emb,
                    reason=default_reason,
                )


def remove_user_faces_from_blocked(user):
    if not user:
        return

    from apps.accounts.users.models import BlockedFace

    BlockedFace.objects.filter(user=user).delete()
