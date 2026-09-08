from django.urls import path

from .views import DashboardSummaryView, SidebarBadgesView

urlpatterns = [
    path("summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("sidebar/", SidebarBadgesView.as_view(), name="dashboard-sidebar"),
]
