from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db import transaction
from .models import Order, OrderStatusEnum, ProductSizeInventory
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Order)
def handle_order_status_change(sender, instance, **kwargs):
    if instance.pk is None:
        return

    try:
        old_order = Order.objects.get(pk=instance.pk)

        if old_order.status == instance.status or old_order.status == OrderStatusEnum.ACCEPTED:
            return

        if instance.status == OrderStatusEnum.ACCEPTED and old_order.status != OrderStatusEnum.ACCEPTED:
            with transaction.atomic():
                order_items = instance.items.select_related('product', 'size').all()

                for item in order_items:
                    try:
                        inventory = ProductSizeInventory.objects.select_for_update().get(
                            product=item.product, size=item.size
                        )

                        if inventory.stock < item.quantity:
                            logger.error(
                                f"Недостаточно товара на складе для заказа {instance.pk}: "
                                f"{item.product.name} ({item.size.name}), "
                                f"в наличии {inventory.stock}, требуется {item.quantity}"
                            )
                            raise ValueError(
                                f"Недостаточно товара: {item.product.name} ({item.size.name}), "
                                f"в наличии {inventory.stock}, требуется {item.quantity}"
                            )
                    except ProductSizeInventory.DoesNotExist:
                        logger.error(
                            f"Не найден товар на складе для заказа {instance.pk}: "
                            f"{item.product.name} ({item.size.name})"
                        )
                        raise ValueError(
                            f"Товар не найден на складе: {item.product.name} ({item.size.name})"
                        )

                for item in order_items:
                    inventory = ProductSizeInventory.objects.select_for_update().get(
                        product=item.product, size=item.size
                    )
                    inventory.stock -= item.quantity
                    inventory.save()
                    logger.info(
                        f"Списано {item.quantity} шт. {item.product.name} ({item.size.name}) "
                        f"для заказа {instance.pk}, осталось {inventory.stock}"
                    )
    except Exception as e:
        logger.error(f"Ошибка при обработке изменения статуса заказа {instance.pk}: {str(e)}")
        raise