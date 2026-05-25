from django.urls import path
from . import views

urlpatterns = [
    # 购物车API
    path('cart/', views.get_cart, name='get_cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/<int:goods_id>/update/', views.update_cart, name='update_cart'),
    path('cart/<int:goods_id>/delete/', views.delete_cart, name='delete_cart'),
    path('cart/select-all/', views.select_all_cart, name='select_all_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('combo/add/', views.add_combo_to_cart, name='add_combo_to_cart'),

    # 订单API
    path('create/', views.create_order, name='create_order'),
    path('list/', views.get_orders, name='get_orders'),
    path('<int:order_id>/', views.get_order_detail, name='get_order_detail'),
    path('<int:order_id>/pay/', views.payment_page, name='payment_page'),
    path('<int:order_id>/pay/confirm/', views.confirm_payment, name='confirm_payment'),
    path('<int:order_id>/pay-old/', views.pay_order, name='pay_order'),
    path('<int:order_id>/set-expire/', views.set_order_expire, name='set_order_expire'),
    path('<int:order_id>/receive/', views.receive_order, name='receive_order'),
    path('<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
]
