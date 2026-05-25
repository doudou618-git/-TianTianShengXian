import json
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from goods.models import GoodsCategory, Goods, FlashSale, Combo, ComboItem
from user.models import UserInfo


class HomePageTest(TestCase):
    """首页测试"""

    def setUp(self):
        self.client = Client()
        self.cat = GoodsCategory.objects.create(name='蔬菜', icon='vegetables', sort=10)
        self.goods = Goods.objects.create(
            category=self.cat, name='番茄', price=4.5, stock=100,
            is_on_sale=True, is_hot=True
        )

    def test_get_home_data(self):
        resp = self.client.get('/home/api/data/')
        data = resp.json()
        self.assertEqual(data['code'], 200)
        self.assertIn('categories', data['data'])
        self.assertIn('goods', data['data'])
        self.assertIn('flash_sales', data['data'])
        self.assertIn('combos', data['data'])

    def test_home_data_categories(self):
        resp = self.client.get('/home/api/data/')
        categories = resp.json()['data']['categories']
        self.assertEqual(len(categories), 1)
        self.assertEqual(categories[0]['name'], '蔬菜')

    def test_home_data_goods(self):
        resp = self.client.get('/home/api/data/')
        goods = resp.json()['data']['goods']
        self.assertEqual(len(goods), 1)
        self.assertEqual(goods[0]['name'], '番茄')
        self.assertEqual(goods[0]['badge'], 'hot')

    def test_home_data_excludes_deleted_goods(self):
        Goods.objects.create(
            category=self.cat, name='已删除', price=1.0, is_delete=True
        )
        resp = self.client.get('/home/api/data/')
        goods = resp.json()['data']['goods']
        self.assertEqual(len(goods), 1)

    def test_home_data_excludes_off_sale_goods(self):
        Goods.objects.create(
            category=self.cat, name='已下架', price=1.0, is_on_sale=False
        )
        resp = self.client.get('/home/api/data/')
        goods = resp.json()['data']['goods']
        self.assertEqual(len(goods), 1)

    def test_home_data_flash_sales(self):
        FlashSale.objects.create(
            goods=self.goods, flash_price=1.9, original_price=4.5,
            stock=100, sold=30,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1),
        )
        resp = self.client.get('/home/api/data/')
        flash_sales = resp.json()['data']['flash_sales']
        self.assertEqual(len(flash_sales), 1)

    def test_home_data_upcoming_sales(self):
        FlashSale.objects.create(
            goods=self.goods, flash_price=1.9, original_price=4.5,
            stock=100,
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2),
        )
        resp = self.client.get('/home/api/data/')
        upcoming = resp.json()['data']['upcoming_sales']
        self.assertEqual(len(upcoming), 1)

    def test_home_data_combos(self):
        g2 = Goods.objects.create(category=self.cat, name='黄瓜', price=3.8, is_on_sale=True)
        combo = Combo.objects.create(name='蔬菜套餐', price=7.0, is_active=True)
        ComboItem.objects.create(combo=combo, goods=self.goods, quantity=1)
        ComboItem.objects.create(combo=combo, goods=g2, quantity=1)
        resp = self.client.get('/home/api/data/')
        combos = resp.json()['data']['combos']
        self.assertEqual(len(combos), 1)
        self.assertEqual(combos[0]['name'], '蔬菜套餐')
