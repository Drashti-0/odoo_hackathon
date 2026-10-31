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

    @api.constrains('list_price', 'standard_price', 'brand_surcharge')
    def _check_product_prices(self):
        for template in self:
            if template.list_price < 0.0:
                raise ValidationError(_("Sales price cannot be negative."))
            if template.standard_price < 0.0:
                raise ValidationError(_("Cost price cannot be negative."))
            if template.brand_surcharge and template.brand_surcharge < 0.0:
                raise ValidationError(_("Brand surcharge cannot be negative."))

    def get_subscription_price(self, plan=None, partner=None):
        """
        Public pricing engine API on product.template.
        Returns the unit subscription price factoring in list price and brand surcharge.
        """
        self.ensure_one()
        if self.subscription_price is not False and self.subscription_price is not None:
            return self.subscription_price
        return (self.list_price or 0.0) + (self.brand_surcharge or 0.0)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    brand_name = fields.Selection(
        related='product_tmpl_id.brand_name',
        string="Brand / Edition Variant",
        readonly=True,
        store=True
    )
    brand_surcharge = fields.Float(
        related='product_tmpl_id.brand_surcharge',
        string="Brand Extra Surcharge",
        readonly=True,
        store=True
    )
    subscription_price = fields.Float(
        string="Calculated Subscription Price",
        compute="_compute_variant_subscription_price",
        store=True,
        digits='Product Price',
        help="Calculated sales price including base template price, variant attribute surcharges, and brand surcharge."
    )

    @api.depends(
        'product_tmpl_id.list_price',
        'product_tmpl_id.brand_name',
        'product_tmpl_id.brand_surcharge',
        'product_template_attribute_value_ids.price_extra',
        'product_template_attribute_value_ids.name'
    )
    def _compute_variant_subscription_price(self):
        for product in self:
            tmpl = product.product_tmpl_id
            base_price = tmpl.list_price or 0.0

            # Check if Odoo brand is configured on the template
            is_odoo_template = (tmpl.brand_name == 'odoo')

            # Check if any variant attribute value is specifically named 'Odoo'
            has_odoo_variant_attr = any(
                ptav.name and ptav.name.strip().lower() == 'odoo'
                for ptav in product.product_template_attribute_value_ids
            )

            variant_extra = sum(product.product_template_attribute_value_ids.mapped('price_extra'))

            # Apply Odoo surcharge of 560 if Odoo brand is active, guarding against duplicate addition
            if is_odoo_template or has_odoo_variant_attr:
                # If variant_extra already contains an extra price >= 560 from an explicit 'Odoo' attribute value, avoid adding it twice
                odoo_attr_surcharges = [
                    ptav.price_extra for ptav in product.product_template_attribute_value_ids
                    if ptav.name and ptav.name.strip().lower() == 'odoo' and ptav.price_extra >= 560.0
                ]
                if odoo_attr_surcharges:
                    brand_extra = 0.0
                else:
                    brand_extra = 560.0
            else:
                brand_extra = tmpl.brand_surcharge or 0.0

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
        if self.subscription_price is not False and self.subscription_price is not None:
            return self.subscription_price
        tmpl = self.product_tmpl_id
        base = tmpl.list_price if tmpl else (self.list_price or 0.0)
        brand = 560.0 if (tmpl and tmpl.brand_name == 'odoo') else 0.0
        return base + brand
