import hashlib

from django.db import models
from db.base_model import BaseModel
from django.contrib.auth.models import AbstractUser
# Create your models here.


class UserInfo(AbstractUser, BaseModel):
    """用户信息"""
    phone = models.CharField(max_length=11, blank=True, default='', verbose_name="手机号")
    is_admin = models.BooleanField(default=False, verbose_name="是否为管理员")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, verbose_name="头像")

    class Meta:
        db_table = "user_info"
        verbose_name = "用户信息"
        verbose_name_plural = verbose_name

    @property
    def avatar_url(self):
        """获取头像URL"""
        if self.avatar:
            return self.avatar.url
        return ""


class Address(BaseModel):
    """地址信息"""
    user = models.ForeignKey(UserInfo, verbose_name="所属用户", on_delete=models.CASCADE) #关联用户信息表
    receiver_name = models.CharField(max_length=20, verbose_name="收件人")
    receiver_mobile = models.CharField(max_length=11, verbose_name="联系电话")
    address = models.CharField(max_length=100, verbose_name="地址")
    is_default = models.BooleanField(default=False, verbose_name="是否默认")

    class Meta:
        db_table = "address"
        verbose_name = "地址信息"
        verbose_name_plural = verbose_name


class Favorite(BaseModel):
    """商品收藏"""
    user = models.ForeignKey(UserInfo, verbose_name="用户", on_delete=models.CASCADE)
    goods = models.ForeignKey('goods.Goods', verbose_name="商品", on_delete=models.CASCADE)

    class Meta:
        db_table = "favorite"
        verbose_name = "商品收藏"
        verbose_name_plural = verbose_name
        unique_together = ('user', 'goods')  # 同一用户同一商品只能收藏一次


class BrowseHistory(BaseModel):
    """浏览记录"""
    user = models.ForeignKey(UserInfo, verbose_name="用户", on_delete=models.CASCADE)
    goods_id = models.IntegerField(verbose_name="商品ID")
    goods_name = models.CharField(max_length=100, verbose_name="商品名称")
    goods_image = models.CharField(max_length=200, default="", verbose_name="商品图片")
    goods_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="商品价格")

    class Meta:
        db_table = "browse_history"
        verbose_name = "浏览记录"
        verbose_name_plural = verbose_name
        ordering = ['-create_time']



