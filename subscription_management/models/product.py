# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_subscription = fields.Boolean(
        string="Is Subscription Service",
        default=True,
        help="Check this box if this product is offered as a recurring subscription service."
    )
    brand_name = fields.Selection(
        selection=[
            ('odoo', 'Odoo'),
            ('brightloop', 'Brightloop Enterprise'),
            ('standard', 'Standard Edition'),
            ('custom', 'Custom Third-Party'),
        ],
        string="Brand / Edition Variant",
        default='standard',
        tracking=True,
        help="Designates the brand or edition. Selecting 'Odoo' adds a mandatory surcharge of 560 to the base price."
    )
    brand_surcharge = fields.Float(
        string="Brand Extra Surcharge",
        compute="_compute_brand_surcharge",
        store=True,
        readonly=False,
        digits='Product Price',
        help="Additional price added based on the selected brand/edition. For 'Odoo' brand, this defaults to 560.0."
    )
    subscription_plan_ids = fields.Many2many(
        comodel_name='subscription.plan',
        relation='product_template_subscription_plan_rel',
        column1='product_tmpl_id',
        column2='plan_id',
        string="Eligible Subscription Plans",
        help="Leave empty to allow this product across all active subscription plans."
    )
    subscription_price = fields.Float(
        string="Calculated Subscription Price",
        compute="_compute_subscription_price",
        store=True,
        digits='Product Price',
        help="Total recurring sales price = Base List Price + Brand Surcharge."
    )

    @api.depends('brand_name')
    def _compute_brand_surcharge(self):
        for template in self:
            if template.brand_name == 'odoo':
                template.brand_surcharge = 560.0
            else:
                template.brand_surcharge = 0.0

    @api.depends('list_price', 'brand_surcharge')
    def _compute_subscription_price(self):
        for template in self:
            template.subscription_price = (template.list_price or 0.0) + (template.brand_surcharge or 0.0)

    @api.constrains('list_price', 'standard_price')
    def _check_product_prices(self):
        for template in self:
            if template.list_price < 0.0:
                raise ValidationError(_("Sales price cannot be negative."))
            if template.standard_price < 0.0:
                raise ValidationError(_("Cost price cannot be negative."))


class ProductProduct(models.Model):
    _inherit = 'product.product'

    subscription_price = fields.Float(
        string="Calculated Subscription Price",
        compute="_compute_variant_subscription_price",
        digits='Product Price',
        help="Calculated sales price including base template price, variant attribute surcharges, and brand surcharge."
    )

    @api.depends('list_price', 'brand_name', 'brand_surcharge', 'product_template_attribute_value_ids.price_extra')
    def _compute_variant_subscription_price(self):
        for product in self:
            # Base template price + brand surcharge (e.g. 560 for Odoo) + any variant attribute price_extra
            base_price = product.product_tmpl_id.list_price or 0.0
            brand_extra = product.product_tmpl_id.brand_surcharge or 0.0
            
            # If variant specifically has brand_name attribute or template surcharge
            if product.product_tmpl_id.brand_name == 'odoo':
                brand_extra = 560.0

            variant_extra = sum(product.product_template_attribute_value_ids.mapped('price_extra'))
            product.subscription_price = base_price + brand_extra + variant_extra

    def get_subscription_price(self, plan=None, partner=None):
        """
        Public pricing engine API for subscriptions and quotations.
        Returns the unit price of this product variant factoring in:
        1. Base List Price
        2. Brand surcharge (Odoo brand adds 560.0)
        3. Variant attribute surcharges
        4. Optional plan-level override or adjustment
        """
        self.ensure_one()
        price = self.subscription_price or (self.list_price + (560.0 if self.brand_name == 'odoo' else 0.0))
        return price
