from django.core.management.base import BaseCommand
from goods.models import GoodsCategory, Goods


class Command(BaseCommand):
    help = '初始化商品分类和示例商品'

    def handle(self, *args, **options):
        # 创建商品分类
        categories_data = [
            {'name': '新鲜蔬菜', 'icon': 'vegetables', 'sort': 10},
            {'name': '时令水果', 'icon': 'fruits', 'sort': 9},
            {'name': '肉禽蛋类', 'icon': 'meat', 'sort': 8},
            {'name': '海鲜水产', 'icon': 'seafood', 'sort': 7},
            {'name': '冷冻食品', 'icon': 'frozen', 'sort': 6},
            {'name': '饮料乳品', 'icon': 'drinks', 'sort': 5},
            {'name': '休闲零食', 'icon': 'snacks', 'sort': 4},
            {'name': '日用百货', 'icon': 'daily', 'sort': 3},
        ]

        for cat_data in categories_data:
            category, created = GoodsCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'icon': cat_data['icon'], 'sort': cat_data['sort']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'创建分类: {category.name}'))
            else:
                self.stdout.write(f'分类已存在: {category.name}')

        # 创建示例商品
        veg_cat = GoodsCategory.objects.get(name='新鲜蔬菜')
        fruit_cat = GoodsCategory.objects.get(name='时令水果')
        meat_cat = GoodsCategory.objects.get(name='肉禽蛋类')

        goods_data = [
            {'name': '有机菠菜', 'category': veg_cat, 'desc': '250g/份', 'price': 6.9, 'unit': '份', 'stock': 100, 'sales': 1230, 'is_new': True},
            {'name': '新鲜番茄', 'category': veg_cat, 'desc': '500g/份', 'price': 4.5, 'unit': '份', 'stock': 200, 'sales': 2100},
            {'name': '本地黄瓜', 'category': veg_cat, 'desc': '400g/份', 'price': 3.8, 'unit': '份', 'stock': 150, 'sales': 1890},
            {'name': '胡萝卜', 'category': veg_cat, 'desc': '350g/份', 'price': 2.9, 'unit': '份', 'stock': 300, 'sales': 3200},
            {'name': '西兰花', 'category': veg_cat, 'desc': '300g/份', 'price': 7.5, 'unit': '份', 'stock': 80, 'sales': 980, 'is_hot': True},
            {'name': '红富士苹果', 'category': fruit_cat, 'desc': '4个装', 'price': 12.8, 'unit': '份', 'stock': 120, 'sales': 3400, 'is_hot': True},
            {'name': '进口香蕉', 'category': fruit_cat, 'desc': '1串约5根', 'price': 8.9, 'unit': '份', 'stock': 200, 'sales': 2800},
            {'name': '阳光玫瑰葡萄', 'category': fruit_cat, 'desc': '500g/盒', 'price': 29.9, 'unit': '盒', 'stock': 50, 'sales': 1560},
            {'name': '猪肋排', 'category': meat_cat, 'desc': '500g/份', 'price': 32.8, 'unit': '份', 'stock': 60, 'sales': 1500, 'is_hot': True},
            {'name': '鸡翅中', 'category': meat_cat, 'desc': '400g/份', 'price': 18.9, 'unit': '份', 'stock': 100, 'sales': 2200},
            {'name': '鲜鸡蛋', 'category': meat_cat, 'desc': '10枚/盒', 'price': 9.9, 'unit': '盒', 'stock': 500, 'sales': 5600, 'is_hot': True},
        ]

        for goods_data_item in goods_data:
            goods, created = Goods.objects.get_or_create(
                name=goods_data_item['name'],
                defaults={
                    'category': goods_data_item['category'],
                    'desc': goods_data_item['desc'],
                    'price': goods_data_item['price'],
                    'unit': goods_data_item['unit'],
                    'stock': goods_data_item['stock'],
                    'sales': goods_data_item['sales'],
                    'is_hot': goods_data_item.get('is_hot', False),
                    'is_new': goods_data_item.get('is_new', False),
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'创建商品: {goods.name}'))
            else:
                self.stdout.write(f'商品已存在: {goods.name}')

        self.stdout.write(self.style.SUCCESS('\n初始化完成！'))
        self.stdout.write(self.style.SUCCESS('您可以登录管理后台添加更多商品和图片'))
