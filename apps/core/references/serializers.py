from apps.core.base.serializers import BaseModelSerializer
from .models import (
    EducationLevel,
    Nationality,
    Profession,
    MaritalStatus,
    HealthStatus,
    Kinship,
)


class EducationLevelSerializer(BaseModelSerializer):
    class Meta:
        model = EducationLevel
        fields = "__all__"


class NationalitySerializer(BaseModelSerializer):
    class Meta:
        model = Nationality
        fields = "__all__"


class ProfessionSerializer(BaseModelSerializer):
    class Meta:
        model = Profession
        fields = "__all__"


class MaritalStatusSerializer(BaseModelSerializer):
    class Meta:
        model = MaritalStatus
        fields = "__all__"


class HealthStatusSerializer(BaseModelSerializer):
    class Meta:
        model = HealthStatus
        fields = "__all__"


class KinshipSerializer(BaseModelSerializer):
    class Meta:
        model = Kinship
        fields = "__all__"
