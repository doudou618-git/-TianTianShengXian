from django.db import models
from db.base_model import BaseModel


class GoodsCategory(BaseModel):
    """商品分类"""
    name = models.CharField(max_length=20, verbose_name="分类名称")
    icon = models.CharField(max_length=50, default="daily", verbose_name="分类图标")
    sort = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "goods_category"
        verbose_name = "商品分类"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Goods(BaseModel):
    """商品"""
    category = models.ForeignKey(GoodsCategory, verbose_name="所属分类", on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name="商品名称")
    desc = models.CharField(max_length=200, default="", verbose_name="商品描述")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="价格")
    unit = models.CharField(max_length=10, default="份", verbose_name="单位")
    stock = models.IntegerField(default=0, verbose_name="库存")
    sales = models.IntegerField(default=0, verbose_name="销量")
    image = models.ImageField(upload_to="goods/", blank=True, null=True, verbose_name="商品图片")
    is_on_sale = models.BooleanField(default=True, verbose_name="是否上架")
    is_hot = models.BooleanField(default=False, verbose_name="是否热销")
    is_new = models.BooleanField(default=False, verbose_name="是否新品")
    sort = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "goods"
        verbose_name = "商品"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    @property
    def image_url(self):
        """获取图片URL"""
        if self.image:
            return self.image.url
        return ""


class GoodsSpec(BaseModel):
    """商品规格"""
    goods = models.ForeignKey(Goods, verbose_name="所属商品", on_delete=models.CASCADE, related_name="specs")
    name = models.CharField(max_length=50, verbose_name="规格名称")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="规格价格")

    class Meta:
        db_table = "goods_spec"
        verbose_name = "商品规格"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.goods.name} - {self.name}"


class FlashSale(BaseModel):
    """秒杀活动"""
    goods = models.ForeignKey(Goods, verbose_name="秒杀商品", on_delete=models.CASCADE)
    flash_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="秒杀价格")
    original_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="原价")
    stock = models.IntegerField(default=0, verbose_name="秒杀库存")
    sold = models.IntegerField(default=0, verbose_name="已售数量")
    start_time = models.DateTimeField(verbose_name="开始时间")
    end_time = models.DateTimeField(verbose_name="结束时间")
    is_active = models.BooleanField(default=True, verbose_name="是否有效")
    image = models.ImageField(upload_to="flashsale/", blank=True, null=True, verbose_name="秒杀图片")

    class Meta:
        db_table = "flash_sale"
        verbose_name = "秒杀活动"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"秒杀: {self.goods.name}"

    @property
    def image_url(self):
        """获取图片URL，优先使用秒杀图片，否则使用商品图片"""
        if self.image:
            return self.image.url
        if self.goods.image:
            return self.goods.image.url
        return ""

    @property
    def progress(self):
        """秒杀进度"""
        if self.stock == 0:
            return 0
        return int(self.sold / self.stock * 100)


class GoodsComment(BaseModel):
    """商品评论"""
    goods = models.ForeignKey(Goods, verbose_name="商品", on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey('user.UserInfo', verbose_name="用户", on_delete=models.CASCADE)
    content = models.TextField(verbose_name="评论内容")
    rating = models.IntegerField(default=5, verbose_name="评分")

    class Meta:
        db_table = "goods_comment"
        verbose_name = "商品评论"
        verbose_name_plural = verbose_name
        ordering = ['-create_time']

    def __str__(self):
        return f"{self.user.username} 评论 {self.goods.name}"


class CommentImage(BaseModel):
    """评论图片"""
    comment = models.ForeignKey(GoodsComment, verbose_name="评论", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="comments/", verbose_name="图片")

    class Meta:
        db_table = "comment_image"
        verbose_name = "评论图片"
        verbose_name_plural = verbose_name

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return ""


class Combo(BaseModel):
    """套餐"""
    name = models.CharField(max_length=100, verbose_name="套餐名称")
    desc = models.CharField(max_length=200, default="", verbose_name="套餐描述")
    image = models.ImageField(upload_to="combo/", blank=True, null=True, verbose_name="套餐图片")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="套餐价格")
    is_active = models.BooleanField(default=True, verbose_name="是否上架")
    sort = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "combo"
        verbose_name = "套餐"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return ""

    @property
    def original_price(self):
        """套餐内商品原价总和"""
        total = 0
        for item in self.comboitem_set.all():
            total += float(item.goods.price) * item.quantity
        return total

    @property
    def goods_list(self):
        """套餐内商品列表"""
        return self.comboitem_set.select_related('goods').all()


class ComboItem(BaseModel):
    """套餐商品"""
    combo = models.ForeignKey(Combo, verbose_name="所属套餐", on_delete=models.CASCADE)
    goods = models.ForeignKey(Goods, verbose_name="商品", on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, verbose_name="数量")

    class Meta:
        db_table = "combo_item"
        verbose_name = "套餐商品"
        verbose_name_plural = verbose_name
