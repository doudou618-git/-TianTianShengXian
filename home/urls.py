from django.urls import path
from . import views

urlpatterns = [
    path('', views.home),                       # 首页
    path('api/data/', views.get_home_data),      # 首页数据API
    path('address/add/', views.add_address_api), # 新建地址API（兼容旧路径）
]