from django.urls import path
from . import views

urlpatterns = [
    #用户路由
    path('login/', views.user_login),# 登录
    path('register/' , views.user_register), #注册
    path('send-sms-code/', views.send_sms_code),# 发送短信验证码
    path('logout/', views.user_logout),#退出登录

    path('address/', views.get_user_address),#获取已经登录的用户地址
    path('address/add/', views.add_address),#新增地址API
    path('address/<int:address_id>/', views.get_address),#获取单个地址
    path('address/<int:address_id>/update/', views.update_address),#更新地址
    path('address/<int:address_id>/delete/', views.delete_address),#删除地址
    path('address/<int:address_id>/set-default/', views.set_default_address),#设置默认地址
    path('address/new/', views.add_address_page),#新增地址页面
    path('center/', views.user_center),#个人中心页面
    path('avatar/upload/', views.upload_avatar),#上传头像
    path('info/', views.get_user_info),#获取用户信息

    # 浏览记录
    path('history/add/', views.add_browse_history),#添加浏览记录
    path('history/', views.get_browse_history),#获取浏览记录
    path('history/<int:goods_id>/delete/', views.delete_browse_history),#删除浏览记录
    path('history/clear/', views.clear_browse_history),#清空浏览记录

    # 商品收藏
    path('favorite/<int:goods_id>/toggle/', views.toggle_favorite),#收藏/取消收藏
    path('favorite/<int:goods_id>/check/', views.check_favorite),#检查是否已收藏
    path('favorites/', views.get_favorites),#获取收藏列表
    path('favorite/<int:favorite_id>/delete/', views.delete_favorite),#删除收藏
]