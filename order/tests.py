import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from .models import Order, OrderGoods, generate_order_no
from goods.models import GoodsCategory, Goods, FlashSale
from user.models import UserInfo


class OrderModelTest(TestCase):
    """订单模型测试"""

    def test_generate_order_no(self):
        no = generate_order_no()
        self.assertEqual(len(no), 22)
        self.assertTrue(no.isalnum())

    def test_order_status_choices(self):
        user = UserInfo.objects.create_user(username='u1', password='p1')
        order = Order.objects.create(user=user, total_amount=100)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.get_status_display(), '待付款')

    def test_order_str(self):
        user = UserInfo.objects.create_user(username='u1', password='p1')
        order = Order.objects.create(user=user)
        self.assertEqual(str(order), order.order_no)


class CreateOrderTest(TestCase):
    """创建订单测试"""

    def setUp(self):
        self.client = Client()
        self.user = UserInfo.objects.create_user(username='u1', password='p1')
        self.client.force_login(self.user)
        self.cat = GoodsCategory.objects.create(name='蔬菜', icon='vegetables')
        self.goods = Goods.objects.create(
            category=self.cat, name='番茄', price=4.5, stock=100, is_on_sale=True
        )

    @patch('utils.redis_helper.get_cart_items')
    @patch('utils.redis_helper.get_combo_cart_info')
    @patch('utils.redis_helper.remove_from_cart')
    def test_create_order_basic(self, mock_remove, mock_combo, mock_cart):
        mock_cart.return_value = {self.goods.id: {'quantity': 2, 'selected': True}}
        mock_combo.return_value = {}

        resp = self.client.post(
            '/order/create/',
            data=json.dumps({
                'goods_ids': [self.goods.id],
                'receiver_name': '张三',
                'receiver_mobile': '13800138000',
                'receiver_address': '北京市朝阳区',
            }),
            content_type='application/json'
        )
        data = resp.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderGoods.objects.count(), 1)

        order = Order.objects.first()
        self.assertEqual(float(order.total_amount), 9.0)
        self.assertEqual(order.receiver_name, '张三')

    @patch('utils.redis_helper.get_cart_items')
    def test_create_order_empty_goods(self, mock_cart):
        mock_cart.return_value = {self.goods.id: {'quantity': 1, 'selected': True}}
        resp = self.client.post(
            '/order/create/',
            data=json.dumps({'goods_ids': []}),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 400)

    @patch('utils.redis_helper.get_cart_items')
    def test_create_order_empty_cart(self, mock_cart):
        mock_cart.return_value = {}
        resp = self.client.post(
            '/order/create/',
            data=json.dumps({'goods_ids': [self.goods.id]}),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 400)


class OrderStatusTest(TestCase):
    """订单状态流转测试"""

    def setUp(self):
        self.client = Client()
        self.user = UserInfo.objects.create_user(username='u1', password='p1')
        self.client.force_login(self.user)
        self.order = Order.objects.create(
            user=self.user, total_amount=100, status='pending',
            receiver_name='张三', receiver_mobile='13800138000',
            receiver_address='北京市朝阳区',
        )

    def test_pay_order(self):
        resp = self.client.post(f'/order/{self.order.id}/pay/confirm/')
        self.assertEqual(resp.json()['code'], 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'paid')

    def test_cancel_pending_order(self):
        resp = self.client.post(f'/order/{self.order.id}/cancel/')
        self.assertEqual(resp.json()['code'], 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')

    def test_cannot_cancel_completed_order(self):
        self.order.status = 'completed'
        self.order.save()
        resp = self.client.post(f'/order/{self.order.id}/cancel/')
        self.assertEqual(resp.json()['code'], 400)

    def test_receive_order(self):
        self.order.status = 'shipped'
        self.order.save()
        resp = self.client.post(f'/order/{self.order.id}/receive/')
        self.assertEqual(resp.json()['code'], 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'completed')

    def test_cannot_receive_pending_order(self):
        resp = self.client.post(f'/order/{self.order.id}/receive/')
        self.assertEqual(resp.json()['code'], 400)

    def test_set_order_expire(self):
        resp = self.client.post(f'/order/{self.order.id}/set-expire/')
        self.assertEqual(resp.json()['code'], 200)
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.expire_time)

    def test_get_order_list(self):
        resp = self.client.get('/order/list/')
        data = resp.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['data']['total'], 1)

    def test_get_order_detail(self):
        resp = self.client.get(f'/order/{self.order.id}/')
        data = resp.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['data']['order_no'], self.order.order_no)

    def test_get_nonexistent_order(self):
        resp = self.client.get('/order/9999/')
        self.assertEqual(resp.json()['code'], 404)

    def test_order_list_filter_by_status(self):
        Order.objects.create(user=self.user, status='paid', total_amount=50)
        resp = self.client.get('/order/list/?status=paid')
        data = resp.json()
        self.assertEqual(data['data']['total'], 1)

    def test_auto_cancel_expired_orders(self):
        self.order.expire_time = timezone.now() - timedelta(minutes=1)
        self.order.save()
        self.client.get('/order/list/')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')


class CartAPITest(TestCase):
    """购物车 API 测试（mock Redis）"""

    def setUp(self):
        self.client = Client()
        self.user = UserInfo.objects.create_user(username='u1', password='p1')
        self.client.force_login(self.user)
        self.cat = GoodsCategory.objects.create(name='蔬菜', icon='vegetables')
        self.goods = Goods.objects.create(
            category=self.cat, name='番茄', price=4.5, stock=100, is_on_sale=True
        )

    @patch('utils.redis_helper.get_cart_items')
    def test_get_empty_cart(self, mock_cart):
        mock_cart.return_value = {}
        resp = self.client.get('/order/cart/')
        data = resp.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['data']['total_price'], 0)

    @patch('utils.redis_helper.add_to_cart')
    def test_add_to_cart(self, mock_add):
        mock_add.return_value = (1, True)
        resp = self.client.post(
            '/order/cart/add/',
            data=json.dumps({'goods_id': self.goods.id, 'quantity': 1}),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 200)

    @patch('utils.redis_helper.add_to_cart')
    def test_add_to_cart_invalid_quantity(self, mock_add):
        resp = self.client.post(
            '/order/cart/add/',
            data=json.dumps({'goods_id': self.goods.id, 'quantity': 0}),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 400)

    @patch('utils.redis_helper.remove_from_cart')
    def test_delete_cart_item(self, mock_remove):
        resp = self.client.post(f'/order/cart/{self.goods.id}/delete/')
        self.assertEqual(resp.json()['code'], 200)

    @patch('utils.redis_helper.select_all_cart')
    def test_select_all_cart(self, mock_select):
        resp = self.client.post(
            '/order/cart/select-all/',
            data=json.dumps({'selected': True}),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 200)

    @patch('utils.redis_helper.clear_cart')
    @patch('utils.redis_helper.clear_combo_cart')
    def test_clear_cart(self, mock_combo, mock_clear):
        resp = self.client.post('/order/cart/clear/')
        self.assertEqual(resp.json()['code'], 200)
