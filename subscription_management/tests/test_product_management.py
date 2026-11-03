# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestProductManagement(TransactionCase):
    """
    Comprehensive Test Suite for Module 1: Product & Product Variant Management.
    Tests model inheritance, attribute variant configuration, brand surcharge logic,
    price recalculations, database persistence, archiving, and public pricing API.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Customer & Plan for Integration Tests
        cls.partner = cls.env['res.partner'].create({
            'name': 'Brightloop Client Corp',
            'email': 'client@brightloop.com',
        })
        cls.plan = cls.env['subscription.plan'].create({
            'name': 'Gold SaaS Tier',
            'price': 100.0,
            'billing_interval_unit': 'monthly',
            'billing_interval_count': 1,
            'min_quantity': 1.0,
        })

    def test_01_product_template_creation(self):
        """Step 1: Test product creation with all required standard and custom fields."""
        tmpl = self.env['product.template'].create({
            'name': 'Cloud ERP Hosting',
            'detailed_type': 'service',
            'list_price': 1200.0,
            'standard_price': 500.0,
            'description': 'Dedicated enterprise cloud server with 99.9% SLA.',
            'is_subscription': True,
            'brand_name': 'standard',
        })
        self.assertEqual(tmpl.name, 'Cloud ERP Hosting')
        self.assertEqual(tmpl.detailed_type, 'service')
        self.assertEqual(tmpl.list_price, 1200.0)
        self.assertEqual(tmpl.standard_price, 500.0)
        self.assertIn('Dedicated enterprise cloud server with 99.9% SLA.', str(tmpl.description))
        self.assertTrue(tmpl.is_subscription)
        self.assertEqual(tmpl.brand_surcharge, 0.0)
        self.assertEqual(tmpl.subscription_price, 1200.0)

        # Variant created automatically for single-variant template
        self.assertTrue(tmpl.product_variant_id)
        variant = tmpl.product_variant_id
        self.assertEqual(variant.subscription_price, 1200.0)

    def test_02_brand_surcharge_test_a_odoo_brand(self):
        """
        Step 3 - Test A:
        Base Price = 1,000
        Brand = Odoo
        Expected Surcharge = 560
        Expected Subscription Price = 1,560
        """
        tmpl = self.env['product.template'].create({
            'name': 'ERP Standard Suite',
            'list_price': 1000.0,
            'brand_name': 'odoo',
            'is_subscription': True,
        })
        self.assertEqual(tmpl.brand_surcharge, 560.0, "Odoo brand must have 560.0 surcharge")
        self.assertEqual(tmpl.subscription_price, 1560.0, "Template subscription price must be 1560.0")

        # Variant reflection
        variant = tmpl.product_variant_id
        self.assertEqual(variant.brand_name, 'odoo')
        self.assertEqual(variant.brand_surcharge, 560.0)
        self.assertEqual(variant.subscription_price, 1560.0)
        self.assertEqual(variant.get_subscription_price(), 1560.0)

    def test_03_brand_surcharge_test_b_brightloop_brand(self):
        """
        Step 3 - Test B:
        Base Price = 1,000
        Brand = Brightloop
        Expected Surcharge = 0
        Expected Subscription Price = 1,000
        """
        tmpl = self.env['product.template'].create({
            'name': 'Brightloop Workflow Suite',
            'list_price': 1000.0,
            'brand_name': 'brightloop',
            'is_subscription': True,
        })
        self.assertEqual(tmpl.brand_surcharge, 0.0, "Brightloop brand must have 0.0 surcharge")
        self.assertEqual(tmpl.subscription_price, 1000.0, "Subscription price must be 1000.0")

        variant = tmpl.product_variant_id
        self.assertEqual(variant.brand_name, 'brightloop')
        self.assertEqual(variant.brand_surcharge, 0.0)
        self.assertEqual(variant.subscription_price, 1000.0)
        self.assertEqual(variant.get_subscription_price(), 1000.0)

    def test_04_brand_surcharge_test_c_brand_switching(self):
        """
        Step 3 - Test C:
        Change Brand from Odoo to Brightloop.
        Verify that the old surcharge is removed.
        """
        tmpl = self.env['product.template'].create({
            'name': 'Switchable Brand Product',
            'list_price': 1000.0,
            'brand_name': 'odoo',
            'is_subscription': True,
        })
        self.assertEqual(tmpl.brand_surcharge, 560.0)
        self.assertEqual(tmpl.subscription_price, 1560.0)
        self.assertEqual(tmpl.product_variant_id.subscription_price, 1560.0)

        # Switch to Brightloop
        tmpl.write({'brand_name': 'brightloop'})
        self.assertEqual(tmpl.brand_surcharge, 0.0, "Surcharge must revert to 0.0 after switching to brightloop")
        self.assertEqual(tmpl.subscription_price, 1000.0, "Subscription price must revert to base 1000.0")
        self.assertEqual(tmpl.product_variant_id.subscription_price, 1000.0, "Variant price must revert to 1000.0")

        # Switch back to Odoo
        tmpl.write({'brand_name': 'odoo'})
        self.assertEqual(tmpl.brand_surcharge, 560.0)
        self.assertEqual(tmpl.subscription_price, 1560.0)
        self.assertEqual(tmpl.product_variant_id.subscription_price, 1560.0)

    def test_05_brand_surcharge_test_d_multiple_variants_and_attributes(self):
        """
        Step 3 - Test D & Step 2:
        Create a product with multiple attributes and variants.
        Verify that surcharge is not duplicated across variants.
        """
        # Create an attribute: "User Tier"
        attr_tier = self.env['product.attribute'].create({
            'name': 'User Tier',
            'value_ids': [
                (0, 0, {'name': '5 Users'}),
                (0, 0, {'name': '25 Users'}),
            ]
        })
        val_5 = attr_tier.value_ids[0]
        val_25 = attr_tier.value_ids[1]

        # Create template with Odoo brand (Base: 1000)
        tmpl = self.env['product.template'].create({
            'name': 'Enterprise Multi-Tier ERP',
            'list_price': 1000.0,
            'brand_name': 'odoo',
            'is_subscription': True,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attr_tier.id,
                'value_ids': [(6, 0, [val_5.id, val_25.id])],
            })]
        })

        # Set variant-specific additional pricing (+400 for 25 Users)
        ptav_25 = tmpl.attribute_line_ids.product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id == val_25
        )
        ptav_25.write({'price_extra': 400.0})

        # Verify 2 variants created
        self.assertEqual(len(tmpl.product_variant_ids), 2)
        var_5 = tmpl.product_variant_ids.filtered(lambda p: val_5 in p.product_template_variant_value_ids.product_attribute_value_id)
        var_25 = tmpl.product_variant_ids.filtered(lambda p: val_25 in p.product_template_variant_value_ids.product_attribute_value_id)

        # Variant 1: Base 1000 + Odoo 560 + Extra 0 = 1560
        self.assertEqual(var_5.subscription_price, 1560.0)
        self.assertEqual(var_5.get_subscription_price(), 1560.0)

        # Variant 2: Base 1000 + Odoo 560 + Extra 400 = 1960
        self.assertEqual(var_25.subscription_price, 1960.0)
        self.assertEqual(var_25.get_subscription_price(), 1960.0)

    def test_06_non_odoo_brands_zero_surcharge(self):
        """Test non-Odoo brands ('standard', 'custom') receive zero surcharge."""
        tmpl_standard = self.env['product.template'].create({
            'name': 'Standard App',
            'list_price': 800.0,
            'brand_name': 'standard',
            'is_subscription': True,
        })
        self.assertEqual(tmpl_standard.brand_surcharge, 0.0)
        self.assertEqual(tmpl_standard.subscription_price, 800.0)

        tmpl_custom = self.env['product.template'].create({
            'name': 'Custom Plugin',
            'list_price': 500.0,
            'brand_name': 'custom',
            'is_subscription': True,
        })
        self.assertEqual(tmpl_custom.brand_surcharge, 0.0)
        self.assertEqual(tmpl_custom.subscription_price, 500.0)

    def test_07_invalid_price_handling(self):
        """Step 7 #9: Test constraints rejecting negative sales price, cost price, and surcharge."""
        # 1. Negative sales price
        with self.assertRaises(ValidationError):
            self.env['product.template'].create({
                'name': 'Negative List Price',
                'list_price': -100.0,
            })

        # 2. Negative standard cost price
        with self.assertRaises(ValidationError):
            self.env['product.template'].create({
                'name': 'Negative Cost Price',
                'list_price': 100.0,
                'standard_price': -50.0,
            })

        # 3. Negative brand surcharge
        with self.assertRaises(ValidationError):
            self.env['product.template'].create({
                'name': 'Negative Surcharge',
                'list_price': 100.0,
                'brand_surcharge': -10.0,
            })

    def test_08_product_archiving(self):
        """Step 2 #8: Test archiving and unarchiving product templates and variants."""
        tmpl = self.env['product.template'].create({
            'name': 'Archivable Service',
            'list_price': 400.0,
            'is_subscription': True,
        })
        var = tmpl.product_variant_id
        self.assertTrue(tmpl.active)
        self.assertTrue(var.active)

        # Archive template
        tmpl.action_archive()
        self.assertFalse(tmpl.active)
        self.assertFalse(var.active, "Archiving template must archive associated variant")

        # Unarchive template
        tmpl.action_unarchive()
        self.assertTrue(tmpl.active)
        self.assertTrue(var.active, "Unarchiving template must unarchive variant")

    def test_09_subscription_integration_and_price_immutability(self):
        """
        Step 6: Test quotation and subscription price integration:
        - Quotation takes correct variant price (Base 1000 + 560 = 1560).
        - Modifying product price later does NOT alter confirmed contract lines.
        """
        tmpl = self.env['product.template'].create({
            'name': 'Dedicated Server',
            'list_price': 1000.0,
            'brand_name': 'odoo',
            'is_subscription': True,
        })
        prod = tmpl.product_variant_id

        # Create subscription with 2 units
        sub = self.env['subscription.subscription'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'line_ids': [(0, 0, {
                'product_id': prod.id,
                'name': prod.name,
                'quantity': 2.0,
                'unit_price': prod.get_subscription_price(),
            })]
        })
        sub.action_confirm()
        self.assertEqual(sub.state, 'confirmed')
        self.assertEqual(sub.line_ids[0].unit_price, 1560.0)
        self.assertEqual(sub.amount_untaxed, 3220.0)  # plan 100 + 2*1560

        # Now change base price on product template to 2000
        tmpl.write({'list_price': 2000.0})
        self.assertEqual(prod.get_subscription_price(), 2560.0)

        # Confirmed contract line price MUST remain unchanged at 1560.0
        self.assertEqual(sub.line_ids[0].unit_price, 1560.0, "Existing confirmed subscription lines must not mutate")
        self.assertEqual(sub.amount_untaxed, 3220.0)
