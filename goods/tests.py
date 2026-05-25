import json
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from .models import GoodsCategory, Goods, GoodsSpec, FlashSale, GoodsComment, Combo, ComboItem
from user.models import UserInfo


class GoodsCategoryModelTest(TestCase):
    """分类模型测试"""

    def test_create_category(self):
        cat = GoodsCategory.objects.create(name='蔬菜', icon='vegetables', sort=10)
        self.assertEqual(str(cat), '蔬菜')
        self.assertEqual(cat.icon, 'vegetables')

    def test_soft_delete_category(self):
        cat = GoodsCategory.objects.create(name='蔬菜', icon='vegetables')
        cat.is_delete = True
        cat.save()
        self.assertTrue(GoodsCategory.objects.get(id=cat.id).is_delete)


class GoodsModelTest(TestCase):
    """商品模型测试"""

    def setUp(self):
        self.cat = GoodsCategory.objects.create(name='蔬菜', icon='vegetables')

    def test_create_goods(self):
        goods = Goods.objects.create(
            category=self.cat, name='番茄', price=4.5, stock=100, sales=50
        )
        self.assertEqual(str(goods), '番茄')
        self.assertEqual(goods.image_url, '')

    def test_goods_spec(self):
        goods = Goods.objects.create(category=self.cat, name='番茄', price=4.5)
        GoodsSpec.objects.create(goods=goods, name='500g', price=4.5)
        GoodsSpec.objects.create(goods=goods, name='1kg', price=8.0)
        self.assertEqual(goods.specs.count(), 2)


class FlashSaleModelTest(TestCase):
    """秒杀模型测试"""

    def setUp(self):
        self.cat = GoodsCategory.objects.create(name='蔬菜', icon='vegetables')
        self.goods = Goods.objects.create(category=self.cat, name='番茄', price=4.5)

    def test_flash_sale_progress(self):
        sale = FlashSale.objects.create(
            goods=self.goods, flash_price=1.9, original_price=4.5,
            stock=100, sold=50,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1),
        )
        self.assertEqual(sale.progress, 50)

    def test_flash_sale_progress_zero_stock(self):
        sale = FlashSale.objects.create(
            goods=self.goods, flash_price=1.9, original_price=4.5,
            stock=0, sold=0,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1),
        )
        self.assertEqual(sale.progress, 0)

    def test_image_url_fallback(self):
        sale = FlashSale.objects.create(
            goods=self.goods, flash_price=1.9, original_price=4.5,
            stock=100,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1),
        )
        self.assertEqual(sale.image_url, '')


class GoodsCommentModelTest(TestCase):
    """评论模型测试"""

    def setUp(self):
        self.client = Client()
        self.user = UserInfo.objects.create_user(username='u1', password='p1')
        self.cat = GoodsCategory.objects.create(name='蔬菜', icon='vegetables')
        self.goods = Goods.objects.create(category=self.cat, name='番茄', price=4.5)
        self.client.force_login(self.user)

    def test_add_comment(self):
        resp = self.client.post(
            f'/goods/{self.goods.id}/comment/',
            data=json.dumps({'content': '很好吃', 'rating': 5}),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 200)
        self.assertEqual(GoodsComment.objects.count(), 1)

    def test_add_comment_empty_content(self):
        resp = self.client.post(
            f'/goods/{self.goods.id}/comment/',
            data=json.dumps({'content': '', 'rating': 5}),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 400)

    def test_add_comment_invalid_rating(self):
        resp = self.client.post(
            f'/goods/{self.goods.id}/comment/',
            data=json.dumps({'content': '好', 'rating': 10}),
            content_type='application/json'
        )
        self.assertEqual(resp.json()['code'], 400)

    def test_delete_own_comment(self):
        comment = GoodsComment.objects.create(
            goods=self.goods, user=self.user, content='好', rating=5
        )
        resp = self.client.post(f'/goods/comment/{comment.id}/delete/')
        self.assertEqual(resp.json()['code'], 200)
        comment.refresh_from_db()
        self.assertTrue(comment.is_delete)

    def test_delete_others_comment(self):
        other = UserInfo.objects.create_user(username='u2', password='p2')
        comment = GoodsComment.objects.create(
            goods=self.goods, user=other, content='好', rating=5
        )
        resp = self.client.post(f'/goods/comment/{comment.id}/delete/')
        self.assertEqual(resp.json()['code'], 403)


class ComboModelTest(TestCase):
    """套餐模型测试"""

    def setUp(self):
        self.cat = GoodsCategory.objects.create(name='蔬菜', icon='vegetables')
        self.g1 = Goods.objects.create(category=self.cat, name='番茄', price=4.5)
        self.g2 = Goods.objects.create(category=self.cat, name='黄瓜', price=3.8)

    def test_combo_original_price(self):
        combo = Combo.objects.create(name='蔬菜套餐', price=7.0)
        ComboItem.objects.create(combo=combo, goods=self.g1, quantity=1)
        ComboItem.objects.create(combo=combo, goods=self.g2, quantity=1)
        self.assertEqual(combo.original_price, 8.3)

    def test_combo_goods_list(self):
        combo = Combo.objects.create(name='蔬菜套餐', price=7.0)
        ComboItem.objects.create(combo=combo, goods=self.g1, quantity=2)
        ComboItem.objects.create(combo=combo, goods=self.g2, quantity=1)
        self.assertEqual(combo.goods_list.count(), 2)


class GoodsAPITest(TestCase):
    """商品 API 测试"""

    def setUp(self):
        self.client = Client()
        self.cat = GoodsCategory.objects.create(name='蔬菜', icon='vegetables', sort=10)
        self.goods = Goods.objects.create(
            category=self.cat, name='番茄', price=4.5, stock=100, is_on_sale=True
        )

    def test_get_categories(self):
        resp = self.client.get('/goods/categories/')
        data = resp.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(len(data['data']), 1)

    def test_get_goods_by_category(self):
        resp = self.client.get(f'/goods/category/{self.cat.id}/')
        data = resp.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(len(data['data']), 1)

    def test_get_goods_detail_api(self):
        resp = self.client.get(f'/goods/{self.goods.id}/api/')
        data = resp.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(data['data']['name'], '番茄')

    def test_get_flash_sales_empty(self):
        resp = self.client.get('/goods/flash-sales/')
        data = resp.json()
        self.assertEqual(data['code'], 200)
        self.assertEqual(len(data['data']), 0)

    def test_get_flash_sales_active(self):
        FlashSale.objects.create(
            goods=self.goods, flash_price=1.9, original_price=4.5,
            stock=100, sold=0,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1),
        )
        resp = self.client.get('/goods/flash-sales/')
        data = resp.json()
        self.assertEqual(len(data['data']), 1)
