import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from .models import GoodsCategory, Goods, FlashSale, GoodsComment, CommentImage


def get_goods_by_category(request, category_id):
    """获取指定分类的商品"""
    goods = Goods.objects.filter(
        category_id=category_id,
        is_delete=False,
        is_on_sale=True
    ).order_by('-sort', '-create_time')

    goods_list = []
    for g in goods:
        goods_list.append({
            'id': g.id,
            'name': g.name,
            'desc': g.desc,
            'price': float(g.price),
            'unit': g.unit,
            'stock': g.stock,
            'sales': g.sales,
            'image': g.image_url,
            'is_hot': g.is_hot,
            'is_new': g.is_new,
            'specs': [s.name for s in g.specs.all()]
        })

    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': goods_list
    })


def get_categories(request):
    """获取所有分类"""
    categories = GoodsCategory.objects.filter(is_delete=False).order_by('sort')

    cat_list = []
    for c in categories:
        cat_list.append({
            'id': c.id,
            'name': c.name,
            'icon': c.icon,
        })

    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': cat_list
    })


def get_flash_sales(request):
    """获取当前有效的秒杀活动"""
    now = timezone.now()
    flash_sales = FlashSale.objects.filter(
        is_delete=False,
        is_active=True,
        start_time__lte=now,
        end_time__gte=now
    ).select_related('goods')

    sale_list = []
    for s in flash_sales:
        sale_list.append({
            'id': s.goods.id,
            'name': s.goods.name,
            'flash_price': float(s.flash_price),
            'original_price': float(s.original_price),
            'sold': s.progress,
            'image': s.goods.image_url,
            'emoji': '🔥'  # 默认图标
        })

    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': sale_list
    })


def goods_detail(request, goods_id):
    """商品详情页"""
    goods = get_object_or_404(Goods, id=goods_id, is_delete=False)

    # 记录浏览历史（仅登录用户）
    if request.user.is_authenticated:
        from user.models import BrowseHistory
        history = BrowseHistory.objects.filter(
            user=request.user,
            goods_id=goods.id,
            is_delete=False
        ).first()

        if history:
            history.save()  # 更新浏览时间
        else:
            BrowseHistory.objects.create(
                user=request.user,
                goods_id=goods.id,
                goods_name=goods.name,
                goods_image=goods.image_url,
                goods_price=goods.price
            )

    # 检查收藏状态
    is_favorited = False
    if request.user.is_authenticated:
        from user.models import Favorite
        is_favorited = Favorite.objects.filter(
            user=request.user,
            goods=goods,
            is_delete=False
        ).exists()

    return render(request, 'goods/detail.html', {
        'goods': goods,
        'is_favorited': is_favorited,
    })


def get_goods_detail_api(request, goods_id):
    """获取商品详情API"""
    goods = get_object_or_404(Goods, id=goods_id, is_delete=False)

    # 获取规格
    specs = [{'id': s.id, 'name': s.name, 'price': float(s.price)} for s in goods.specs.all()]

    # 获取评论
    comments = GoodsComment.objects.filter(goods=goods, is_delete=False).select_related('user')[:20]
    comment_list = []
    current_user_id = request.user.id if request.user.is_authenticated else None
    for c in comments:
        images = [{'id': img.id, 'url': img.image_url} for img in c.images.all()]
        comment_list.append({
            'id': c.id,
            'user_id': c.user.id,
            'username': c.user.username,
            'avatar_url': c.user.avatar_url,
            'content': c.content,
            'rating': c.rating,
            'images': images,
            'create_time': c.create_time.strftime('%Y-%m-%d %H:%M'),
            'is_owner': c.user.id == current_user_id,
        })

    # 评论统计
    total_comments = GoodsComment.objects.filter(goods=goods, is_delete=False).count()
    avg_rating = 0
    if total_comments > 0:
        from django.db.models import Avg
        avg_rating = GoodsComment.objects.filter(goods=goods, is_delete=False).aggregate(Avg('rating'))['rating__avg']

    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': {
            'id': goods.id,
            'name': goods.name,
            'desc': goods.desc,
            'price': float(goods.price),
            'unit': goods.unit,
            'stock': goods.stock,
            'sales': goods.sales,
            'image': goods.image_url,
            'category': goods.category.name,
            'specs': specs,
            'comments': comment_list,
            'comment_count': total_comments,
            'avg_rating': round(avg_rating, 1),
        }
    })


@login_required
def add_comment(request, goods_id):
    """添加评论"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    goods = get_object_or_404(Goods, id=goods_id, is_delete=False)
    user = request.user

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'msg': '请求数据格式错误'})

    content = data.get('content', '').strip()
    rating = data.get('rating', 5)

    if not content:
        return JsonResponse({'code': 400, 'msg': '评论内容不能为空'})

    if not (1 <= rating <= 5):
        return JsonResponse({'code': 400, 'msg': '评分范围为1-5'})

    # 创建评论
    comment = GoodsComment.objects.create(
        goods=goods,
        user=user,
        content=content,
        rating=rating
    )

    return JsonResponse({
        'code': 200,
        'msg': '评论成功',
        'data': {
            'id': comment.id,
            'username': user.username,
            'content': comment.content,
            'rating': comment.rating,
            'create_time': comment.create_time.strftime('%Y-%m-%d %H:%M'),
        }
    })


@login_required
def upload_comment_image(request, comment_id):
    """上传评论图片"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    comment = get_object_or_404(GoodsComment, id=comment_id, user=request.user, is_delete=False)

    if 'image' not in request.FILES:
        return JsonResponse({'code': 400, 'msg': '请选择图片'})

    image_file = request.FILES['image']

    # 限制图片大小 (5MB)
    if image_file.size > 5 * 1024 * 1024:
        return JsonResponse({'code': 400, 'msg': '图片大小不能超过5MB'})

    # 限制图片数量
    if comment.images.count() >= 9:
        return JsonResponse({'code': 400, 'msg': '最多上传9张图片'})

    comment_image = CommentImage.objects.create(
        comment=comment,
        image=image_file
    )

    return JsonResponse({
        'code': 200,
        'msg': '上传成功',
        'data': {
            'id': comment_image.id,
            'url': comment_image.image_url,
        }
    })


@login_required
def delete_comment(request, comment_id):
    """删除评论"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    comment = get_object_or_404(GoodsComment, id=comment_id, is_delete=False)

    # 只能删除自己的评论
    if comment.user != request.user:
        return JsonResponse({'code': 403, 'msg': '只能删除自己的评论'})

    # 软删除评论
    comment.is_delete = True
    comment.save()

    return JsonResponse({
        'code': 200,
        'msg': '删除成功'
    })
