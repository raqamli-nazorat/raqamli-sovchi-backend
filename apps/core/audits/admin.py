from django.contrib import admin
from unfold.admin import ModelAdmin
from auditlog.models import LogEntry
from auditlog.admin import LogEntryAdmin
from django.contrib.admin.sites import NotRegistered

try:
    admin.site.unregister(LogEntry)
except NotRegistered:
    pass

@admin.register(LogEntry)
class UnfoldLogEntryAdmin(ModelAdmin, LogEntryAdmin):
    list_display = ["created", "resource_url", "action", "msg_short", "user_url"]
    list_filter = ["action"]
    search_fields = [
        "timestamp",
        "object_repr",
        "changes",
        "actor__first_name",
        "actor__last_name",
    ]
