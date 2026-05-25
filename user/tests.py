import json
from django.test import TestCase, Client
from django.urls import reverse
from .models import UserInfo, Address, Favorite


class UserModelTest(TestCase):
    """用户模型测试"""

    def test_create_user(self):
        user = UserInfo.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_admin)

    def test_avatar_url_empty(self):
        user = UserInfo.objects.create_user(username='u1', password='p1')
        self.assertEqual(user.avatar_url, '')

    def test_soft_delete(self):
        user = UserInfo.objects.create_user(username='u1', password='p1')
        user.is_delete = True
        user.save()
        self.assertTrue(UserInfo.objects.get(id=user.id).is_delete)


class UserLoginTest(TestCase):
    """用户登录测试"""

    def setUp(self):
        self.client = Client()
        UserInfo.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

    def test_login_success(self):
        resp = self.client.post(
            '/user/login/',
            data=json.dumps({'username': 'testuser', 'password': 'testpass123'}),
            content_type='application/json'
        )
        data = resp.json()
        self.assertEqual(data['code'], 200)

    def test_login_wrong_password(self):
        resp = self.client.post(
            '/user/login/',
            data=json.dumps({'username': 'testuser', 'password': 'wrong'}),
            content_type='application/json'
        )
        data = resp.json()
        self.assertEqual(data['code'], 400)

    def test_login_nonexistent_user(self):
        resp = self.client.post(
            '/user/login/',
            data=json.dumps({'username': 'nobody', 'password': 'pass'}),
            content_type='application/json'
        )
        data = resp.json()
        self.assertEqual(data['code'], 400)


class UserRegisterTest(TestCase):
    """用户注册测试"""

    def setUp(self):
        self.client = Client()
        self.valid_data = {
            'username': 'newuser',
            'password': 'newpass123',
            'email': 'new@example.com',
            'phone': '13800138000',
            'sms_code': '123456',
        }

    def test_register_duplicate_username(self):
        UserInfo.objects.create_user(username='newuser', password='p1')
        resp = self.client.post(
            '/user/register/',
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 400)
        self.assertIn('用户已存在', resp.json()['msg'])

    def test_register_duplicate_phone(self):
        UserInfo.objects.create_user(username='other', password='p1', phone='13800138000')
        resp = self.client.post(
            '/user/register/',
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 400)
        self.assertIn('手机号已注册', resp.json()['msg'])


class AddressTest(TestCase):
    """地址管理测试"""

    def setUp(self):
        self.client = Client()
        self.user = UserInfo.objects.create_user(username='u1', password='p1')
        self.client.force_login(self.user)

    def test_add_address(self):
        resp = self.client.post(
            '/user/address/add/',
            data=json.dumps({
                'receiver_name': '张三',
                'receiver_mobile': '13800138000',
                'address': '北京市朝阳区某小区1号楼',
                'is_default': True,
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 200)
        self.assertEqual(Address.objects.count(), 1)

    def test_add_address_invalid_phone(self):
        resp = self.client.post(
            '/user/address/add/',
            data=json.dumps({
                'receiver_name': '张三',
                'receiver_mobile': '123',
                'address': '北京市朝阳区某小区1号楼',
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 400)

    def test_get_addresses(self):
        Address.objects.create(
            user=self.user, receiver_name='张三',
            receiver_mobile='13800138000', address='地址1'
        )
        resp = self.client.get('/user/address/')
        data = resp.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(len(data['data']), 1)

    def test_delete_address(self):
        addr = Address.objects.create(
            user=self.user, receiver_name='张三',
            receiver_mobile='13800138000', address='地址1'
        )
        resp = self.client.post(f'/user/address/{addr.id}/delete/')
        self.assertEqual(resp.json()['code'], 200)
        self.assertEqual(Address.objects.count(), 0)

    def test_set_default_address(self):
        addr1 = Address.objects.create(
            user=self.user, receiver_name='A',
            receiver_mobile='13800138000', address='地址1', is_default=True
        )
        addr2 = Address.objects.create(
            user=self.user, receiver_name='B',
            receiver_mobile='13800138001', address='地址2'
        )
        resp = self.client.post(f'/user/address/{addr2.id}/set-default/')
        self.assertEqual(resp.json()['code'], 200)
        addr1.refresh_from_db()
        addr2.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)


class FavoriteTest(TestCase):
    """收藏测试"""

    def setUp(self):
        self.client = Client()
        self.user = UserInfo.objects.create_user(username='u1', password='p1')
        self.client.force_login(self.user)
        from goods.models import GoodsCategory, Goods
        self.cat = GoodsCategory.objects.create(name='蔬菜', icon='vegetables')
        self.goods = Goods.objects.create(
            category=self.cat, name='番茄', price=4.5, stock=100
        )

    def test_toggle_favorite(self):
        resp = self.client.post(f'/user/favorite/{self.goods.id}/toggle/')
        self.assertEqual(resp.json()['code'], 200)
        self.assertTrue(resp.json()['data']['is_favorited'])

    def test_toggle_unfavorite(self):
        Favorite.objects.create(user=self.user, goods=self.goods)
        resp = self.client.post(f'/user/favorite/{self.goods.id}/toggle/')
        self.assertEqual(resp.json()['code'], 200)
        self.assertFalse(resp.json()['data']['is_favorited'])

    def test_check_favorite(self):
        resp = self.client.get(f'/user/favorite/{self.goods.id}/check/')
        self.assertFalse(resp.json()['data']['is_favorited'])

    def test_get_favorites(self):
        Favorite.objects.create(user=self.user, goods=self.goods)
        resp = self.client.get('/user/favorites/')
        data = resp.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(len(data['data']['list']), 1)
