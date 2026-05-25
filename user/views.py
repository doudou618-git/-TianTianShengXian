from django.shortcuts import render , redirect
from django.contrib.auth import authenticate ,  login ,logout
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import json
import random
import logging

from utils import redis_helper

logger = logging.getLogger(__name__)


#用户登录页面
def user_login( request):
    if request.method == 'GET':
        return render(request, 'login.html')
    #获取前端数据
    elif request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')

        #验证用户
        user = authenticate(request , username=username, password=password)
        if user is not None:
            #登录成功
            login(request, user)
            return JsonResponse({
                'code': 200,
                'msg': '登录成功',
                'url': '/home/',
                'data':{
                    'username': user.username,
                    'email': user.email,
                    'is_authenticated': True,    #添加登录状态标记
                }
            })
        else:
            return JsonResponse({
                'code': 400,
                'msg': '用户名或密码错误',
            })







def user_register( request):
    if request.method == 'GET':
        return render(request, 'register.html')

    elif request.method == 'POST':
        from .models import UserInfo
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        phone = data.get('phone')
        sms_code = data.get('sms_code')

        #检查用户是否存在
        if UserInfo.objects.filter(username=username).exists():
            return JsonResponse({
                'code': 400,
                'msg': '用户已存在',
            })

        # 检查邮箱是否已注册
        if email and UserInfo.objects.filter(email=email).exists():
            return JsonResponse({
                'code': 400,
                'msg': '该邮箱已注册',
            })

        # 检查手机号是否已注册
        if UserInfo.objects.filter(phone=phone).exists():
            return JsonResponse({
                'code': 400,
                'msg': '该手机号已注册',
            })

        # 验证短信验证码
        if not sms_code:
            return JsonResponse({
                'code': 400,
                'msg': '请输入短信验证码',
            })

        stored_code = redis_helper.get_sms_code(phone)
        if not stored_code:
            return JsonResponse({
                'code': 400,
                'msg': '验证码已过期，请重新获取',
            })
        if str(stored_code) != str(sms_code):
            return JsonResponse({
                'code': 400,
                'msg': '验证码错误',
            })

        # 验证通过，删除验证码
        redis_helper.delete_sms_code(phone)

        user = UserInfo.objects.create_user(
            username=username,
            password=password,
            email=email,
        )
        # 保存手机号
        user.phone = phone
        user.save()

        return JsonResponse({
            'code': 200,
            'msg': '注册成功',
            'url': '/user/login/',
            'data':{
                'username': user.username,
                'email': user.email,
            }
        })


def send_sms_code(request):
    """发送短信验证码"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    from .models import UserInfo

    data = json.loads(request.body)
    phone = data.get('phone', '').strip()

    # 校验手机号格式
    if not phone or not phone.isdigit() or len(phone) != 11:
        return JsonResponse({'code': 400, 'msg': '请输入正确的11位手机号码'})

    # 检查手机号是否已注册
    if UserInfo.objects.filter(phone=phone).exists():
        return JsonResponse({'code': 400, 'msg': '该手机号已注册'})

    # 生成6位验证码
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

    # 存储到 Redis（5分钟有效）
    redis_helper.save_sms_code(phone, code, ttl=300)

    # 开发环境：输出到控制台
    # 生产环境：替换为实际的短信 API 调用（如阿里云短信、腾讯云短信等）
    logger.info(f'[短信验证码] 手机号: {phone}, 验证码: {code}')
    print(f'[短信验证码] 手机号: {phone}, 验证码: {code}')

    return JsonResponse({'code': 200, 'msg': '验证码已发送到您的手机'})


@login_required
def user_logout(request):
    """用户登出"""
    logout(request)
    return redirect('/home/')



@login_required
def get_user_address(request):
    """获取当前用户的用户地址"""
    from .models import Address
    addresses = Address.objects.filter(user = request.user).order_by('-is_default')

    address_list = []
    for addr in addresses:
        address_list.append({
            'id': addr.id,
            'receiver_name': addr.receiver_name,
            'receiver_mobile': addr.receiver_mobile,
            'address': addr.address,
            'is_default': addr.is_default,
        })
    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': address_list,
    })


@login_required
def user_center(request):
    """个人中心页面"""
    return render(request, 'user_center.html')


@login_required
def add_address(request):
    """新增地址API"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    from .models import Address

    data = json.loads(request.body)
    receiver_name = data.get('receiver_name', '').strip()
    receiver_mobile = data.get('receiver_mobile', '').strip()
    address = data.get('address', '').strip()
    is_default = data.get('is_default', False)

    # 参数校验
    if not receiver_name or len(receiver_name) < 2:
        return JsonResponse({'code': 400, 'msg': '请输入有效的收件人姓名'})
    if not receiver_mobile or not receiver_mobile.isdigit() or len(receiver_mobile) != 11:
        return JsonResponse({'code': 400, 'msg': '请输入正确的11位手机号码'})
    if not address or len(address) < 5:
        return JsonResponse({'code': 400, 'msg': '请输入完整的详细地址'})

    # 如果设为默认，先取消其他默认地址
    if is_default:
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

    Address.objects.create(
        user=request.user,
        receiver_name=receiver_name,
        receiver_mobile=receiver_mobile,
        address=address,
        is_default=is_default,
    )

    return JsonResponse({'code': 200, 'msg': '地址添加成功'})


@login_required
def update_address(request, address_id):
    """更新地址API"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    from .models import Address

    try:
        addr = Address.objects.get(id=address_id, user=request.user)
    except Address.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '地址不存在'})

    data = json.loads(request.body)
    receiver_name = data.get('receiver_name', '').strip()
    receiver_mobile = data.get('receiver_mobile', '').strip()
    address = data.get('address', '').strip()
    is_default = data.get('is_default', False)

    # 参数校验
    if not receiver_name or len(receiver_name) < 2:
        return JsonResponse({'code': 400, 'msg': '请输入有效的收件人姓名'})
    if not receiver_mobile or not receiver_mobile.isdigit() or len(receiver_mobile) != 11:
        return JsonResponse({'code': 400, 'msg': '请输入正确的11位手机号码'})
    if not address or len(address) < 5:
        return JsonResponse({'code': 400, 'msg': '请输入完整的详细地址'})

    # 如果设为默认，先取消其他默认地址
    if is_default:
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

    addr.receiver_name = receiver_name
    addr.receiver_mobile = receiver_mobile
    addr.address = address
    addr.is_default = is_default
    addr.save()

    return JsonResponse({'code': 200, 'msg': '地址更新成功'})


@login_required
def delete_address(request, address_id):
    """删除地址API"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    from .models import Address

    try:
        addr = Address.objects.get(id=address_id, user=request.user)
        addr.delete()
        return JsonResponse({'code': 200, 'msg': '地址删除成功'})
    except Address.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '地址不存在'})


@login_required
def set_default_address(request, address_id):
    """设置默认地址API"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    from .models import Address

    try:
        # 先取消所有默认地址
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        # 设置新的默认地址
        addr = Address.objects.get(id=address_id, user=request.user)
        addr.is_default = True
        addr.save()
        return JsonResponse({'code': 200, 'msg': '默认地址设置成功'})
    except Address.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '地址不存在'})


@login_required
def get_address(request, address_id):
    """获取单个地址信息"""
    from .models import Address

    try:
        addr = Address.objects.get(id=address_id, user=request.user)
        return JsonResponse({
            'code': 200,
            'msg': '获取成功',
            'data': {
                'id': addr.id,
                'receiver_name': addr.receiver_name,
                'receiver_mobile': addr.receiver_mobile,
                'address': addr.address,
                'is_default': addr.is_default,
            }
        })
    except Address.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '地址不存在'})


@login_required
def add_address_page(request):
    """新增地址页面"""
    # 获取来源参数，用于确定返回页面
    source = request.GET.get('source', 'home')
    return render(request, 'add_address.html', {'source': source})


@login_required
def upload_avatar(request):
    """上传头像API"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    if 'avatar' not in request.FILES:
        return JsonResponse({'code': 400, 'msg': '请选择头像图片'})

    avatar_file = request.FILES['avatar']

    # 限制图片大小 (2MB)
    if avatar_file.size > 2 * 1024 * 1024:
        return JsonResponse({'code': 400, 'msg': '头像大小不能超过2MB'})

    # 更新用户头像
    user = request.user
    user.avatar = avatar_file
    user.save()

    return JsonResponse({
        'code': 200,
        'msg': '头像上传成功',
        'data': {
            'avatar_url': user.avatar_url,
        }
    })


@login_required
def get_user_info(request):
    """获取用户信息API"""
    user = request.user
    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': {
            'username': user.username,
            'email': user.email,
            'avatar_url': user.avatar_url,
            'is_admin': user.is_admin,
        }
    })


@login_required
def add_browse_history(request):
    """添加浏览记录（存入Redis）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'msg': '请求数据格式错误'})

    goods_id = data.get('goods_id')
    goods_name = data.get('goods_name', '')
    goods_image = data.get('goods_image', '')
    goods_price = data.get('goods_price', 0)

    if not goods_id:
        return JsonResponse({'code': 400, 'msg': '商品ID不能为空'})

    redis_helper.add_browse_history(
        user_id=request.user.id,
        goods_id=goods_id,
        goods_name=goods_name,
        goods_image=goods_image,
        goods_price=goods_price,
    )

    return JsonResponse({'code': 200, 'msg': '记录成功'})


@login_required
def get_browse_history(request):
    """获取浏览记录（从Redis读取，支持分页）"""
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 5))

    history_list, total = redis_helper.get_browse_history(request.user.id, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': {
            'list': history_list,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
        }
    })


@login_required
def delete_browse_history(request, goods_id):
    """删除单条浏览记录（按goods_id从Redis删除）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    deleted = redis_helper.delete_browse_history(request.user.id, goods_id)
    if deleted:
        return JsonResponse({'code': 200, 'msg': '删除成功'})
    return JsonResponse({'code': 404, 'msg': '记录不存在'})


@login_required
def clear_browse_history(request):
    """清空浏览记录（从Redis删除）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    redis_helper.clear_browse_history(request.user.id)
    return JsonResponse({'code': 200, 'msg': '清空成功'})


# ==================== 商品收藏 ====================

@login_required
def toggle_favorite(request, goods_id):
    """切换商品收藏状态（收藏/取消收藏）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    from .models import Favorite
    from goods.models import Goods

    try:
        goods = Goods.objects.get(id=goods_id, is_delete=False)
    except Goods.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '商品不存在'})

    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        goods=goods,
        defaults={'is_delete': False}
    )

    if not created:
        # 已存在，切换状态
        favorite.is_delete = not favorite.is_delete
        favorite.save()

    is_favorited = not favorite.is_delete
    return JsonResponse({
        'code': 200,
        'msg': '收藏成功' if is_favorited else '已取消收藏',
        'data': {
            'is_favorited': is_favorited,
        }
    })


@login_required
def check_favorite(request, goods_id):
    """检查商品是否已收藏"""
    from .models import Favorite

    is_favorited = Favorite.objects.filter(
        user=request.user,
        goods_id=goods_id,
        is_delete=False
    ).exists()

    return JsonResponse({
        'code': 200,
        'data': {
            'is_favorited': is_favorited,
        }
    })


@login_required
def get_favorites(request):
    """获取用户收藏列表"""
    from .models import Favorite

    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))

    favorites = Favorite.objects.filter(
        user=request.user,
        is_delete=False
    ).select_related('goods').order_by('-create_time')

    total = favorites.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    start = (page - 1) * page_size
    items = favorites[start:start + page_size]

    favorite_list = []
    for fav in items:
        goods = fav.goods
        if goods.is_delete:
            continue
        favorite_list.append({
            'id': fav.id,
            'goods_id': goods.id,
            'goods_name': goods.name,
            'goods_image': goods.image_url,
            'goods_price': float(goods.price),
            'goods_desc': goods.desc,
            'is_on_sale': goods.is_on_sale,
            'create_time': fav.create_time.strftime('%Y-%m-%d %H:%M'),
        })

    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': {
            'list': favorite_list,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
        }
    })


@login_required
def delete_favorite(request, favorite_id):
    """删除收藏"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    from .models import Favorite

    try:
        fav = Favorite.objects.get(id=favorite_id, user=request.user, is_delete=False)
        fav.is_delete = True
        fav.save()
        return JsonResponse({'code': 200, 'msg': '删除成功'})
    except Favorite.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '收藏记录不存在'})