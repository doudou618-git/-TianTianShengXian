from django.urls import path
from . import views

urlpatterns = [
    # 商品API
    path('categories/', views.get_categories, name='get_categories'),
    path('category/<int:category_id>/', views.get_goods_by_category, name='get_goods_by_category'),
    path('flash-sales/', views.get_flash_sales, name='get_flash_sales'),

    # 商品详情页
    path('<int:goods_id>/', views.goods_detail, name='goods_detail'),
    path('<int:goods_id>/api/', views.get_goods_detail_api, name='goods_detail_api'),

    # 评论相关
    path('<int:goods_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/image/', views.upload_comment_image, name='upload_comment_image'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
]
