from django.urls import path
from . import views

app_name = 'manage_app'

urlpatterns = [
    # 管理员登录
    path('login/', views.admin_login, name='admin_login'),

    # 管理后台首页
    path('', views.admin_index, name='admin_index'),

    # 商品管理
    path('goods/', views.goods_list, name='goods_list'),
    path('goods/add/', views.goods_add, name='goods_add'),
    path('goods/<int:goods_id>/edit/', views.goods_edit, name='goods_edit'),
    path('goods/<int:goods_id>/toggle/', views.goods_toggle, name='goods_toggle'),
    path('goods/<int:goods_id>/delete/', views.goods_delete, name='goods_delete'),

    # 分类管理
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:cat_id>/edit/', views.category_edit, name='category_edit'),

    # 秒杀管理
    path('flashsale/', views.flashsale_list, name='flashsale_list'),
    path('flashsale/add/', views.flashsale_add, name='flashsale_add'),
    path('flashsale/<int:sale_id>/edit/', views.flashsale_edit, name='flashsale_edit'),
    path('flashsale/<int:sale_id>/delete/', views.flashsale_delete, name='flashsale_delete'),

    # 套餐管理
    path('combo/', views.combo_list, name='combo_list'),
    path('combo/add/', views.combo_add, name='combo_add'),
    path('combo/<int:combo_id>/edit/', views.combo_edit, name='combo_edit'),
    path('combo/<int:combo_id>/delete/', views.combo_delete, name='combo_delete'),
]
