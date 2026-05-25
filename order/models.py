import uuid
from django.db import models
from db.base_model import BaseModel


class Cart(BaseModel):
    """购物车"""
    user = models.ForeignKey('user.UserInfo', verbose_name="用户", on_delete=models.CASCADE)
    goods = models.ForeignKey('goods.Goods', verbose_name="商品", on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, verbose_name="数量")
    selected = models.BooleanField(default=True, verbose_name="是否选中")

    class Meta:
        db_table = "cart"
        verbose_name = "购物车"
        verbose_name_plural = verbose_name


def generate_order_no():
    """生成订单号"""
    import time
    return time.strftime('%Y%m%d%H%M%S') + uuid.uuid4().hex[:8].upper()


class Order(BaseModel):
    """订单"""
    STATUS_CHOICES = [
        ('pending', '待付款'),
        ('paid', '待发货'),
        ('shipped', '待收货'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    order_no = models.CharField(max_length=30, unique=True, default=generate_order_no, verbose_name="订单号")
    user = models.ForeignKey('user.UserInfo', verbose_name="用户", on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="订单总金额")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="订单状态")
    receiver_name = models.CharField(max_length=20, default="", verbose_name="收件人")
    receiver_mobile = models.CharField(max_length=11, default="", verbose_name="联系电话")
    receiver_address = models.CharField(max_length=200, default="", verbose_name="收货地址")
    remark = models.CharField(max_length=200, default="", verbose_name="备注")
    expire_time = models.DateTimeField(null=True, blank=True, verbose_name="过期时间")

    class Meta:
        db_table = "order_info"
        verbose_name = "订单"
        verbose_name_plural = verbose_name
        ordering = ['-create_time']

    def __str__(self):
        return self.order_no


class OrderGoods(BaseModel):
    """订单商品"""
    order = models.ForeignKey(Order, verbose_name="订单", on_delete=models.CASCADE, related_name='goods_items')
    goods = models.ForeignKey('goods.Goods', verbose_name="商品", on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, verbose_name="数量")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="单价")

    class Meta:
        db_table = "order_goods"
        verbose_name = "订单商品"
        verbose_name_plural = verbose_name
