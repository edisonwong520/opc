from django.contrib import admin

from .models import (
    AgentRun,
    AgentTemplate,
    ApprovalDecision,
    AuditLog,
    BoardBrief,
    FounderProfile,
    Mission,
    MissionEvent,
    Organization,
    PricingProfile,
    QualityGate,
    Workstream,
)


@admin.register(PricingProfile)
class PricingProfileAdmin(admin.ModelAdmin):
    list_display = ("provider", "model_id", "input_per_1k_usd", "output_per_1k_usd", "is_active", "updated_at")
    list_filter = ("provider", "is_active")
    search_fields = ("provider", "model_id")


admin.site.register(AgentTemplate)
admin.site.register(Mission)
admin.site.register(Workstream)
admin.site.register(AgentRun)
admin.site.register(MissionEvent)
admin.site.register(QualityGate)
admin.site.register(BoardBrief)
admin.site.register(ApprovalDecision)
admin.site.register(AuditLog)
admin.site.register(Organization)


@admin.register(FounderProfile)
class FounderProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "created_at")
    list_filter = ("role", "organization")
    search_fields = ("user__username", "organization__name")
