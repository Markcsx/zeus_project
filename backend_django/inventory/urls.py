from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, SalesRecordViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'sales-records', SalesRecordViewSet, basename='sales-record')

urlpatterns = router.urls