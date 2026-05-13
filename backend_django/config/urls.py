from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from django.views.generic import RedirectView
from inventory.frontend_views import InventoryAppView

urlpatterns = [
    path("", RedirectView.as_view(url="/app/", permanent=False)),
    path("login/", LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("app/", InventoryAppView.as_view(), name="inventory-app"),
    path("admin/", admin.site.urls),
    path("api/", include("inventory.urls")),
]
