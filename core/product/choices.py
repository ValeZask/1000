from django.db import models


class ProductStatusEnum(models.TextChoices):
    SOON_ON_SALE = 'soon_on_sale', 'Скоро в продаже'
    ON_SALE = 'on_sale', 'В продаже'
    OUT_OF_STOCK = 'out_of_stock', 'Нет в наличии'


class BannerPositionEnum(models.TextChoices):
    HEADER_MAIN_PAGE = 'header_main_page', 'В шапке на главной странице'
    MIDDLE_MAIN_PAGE = 'middle_main_page', 'В середине на главной странице'
    HEADER_DETAIL_PAGE = 'header_detail_page', 'В шапке в детальной странице'


class OrderStatusEnum(models.TextChoices):
    IN_PROGRESS = 'in_progress', 'В процессе'
    ACCEPTED = 'accepted', 'Принято'
    REJECTED = 'rejected', 'Отклонено'
