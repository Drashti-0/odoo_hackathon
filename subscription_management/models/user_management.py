# -*- coding: utf-8 -*-
import re
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError

_logger = logging.getLogger(__name__)

# Regular expression for standard RFC 5322 compatible email validation
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


def validate_email_syntax(email):
    """
    Validates email format according to standard RFC structure.
    Raises ValidationError if invalid.
    """
    if not email or not isinstance(email, str):
        raise ValidationError(_("Email address cannot be empty."))
    clean_email = email.strip()
    if not EMAIL_REGEX.match(clean_email):
        raise ValidationError(_("Invalid email format: '%s'. Please provide a valid email address (e.g. user@example.com).") % email)
    return clean_email


def validate_password_strength(password):
    """
    Enforces Brightloop Password Security Policy:
    1. Must contain more than 8 characters (length >= 9).
    2. Must contain at least one uppercase letter (A-Z).
    3. Must contain at least one lowercase letter (a-z).
    4. Must contain at least one special character (!@#$%^&*()_+-=[]{}|;:'",.<>?/~`\\).
    5. Does not store or log plaintext passwords.
    """
    if not password or not isinstance(password, str):
        raise ValidationError(_("Password cannot be empty."))

    errors = []
    # Requirement: "Password must contain more than 8 characters" -> len > 8
    if len(password) <= 8:
        errors.append(_("Must contain more than 8 characters (at least 9 characters)."))
    if not re.search(r'[A-Z]', password):
        errors.append(_("Must contain at least one uppercase letter (A-Z)."))
    if not re.search(r'[a-z]', password):
        errors.append(_("Must contain at least one lowercase letter (a-z)."))
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:\'",.<>?/~`\\]', password):
        errors.append(_("Must contain at least one special character (!@#$%^&* etc.)."))

    if errors:
        raise ValidationError(
            _("Password does not satisfy the security requirements:\n- ") + "\n- ".join(errors)
        )
    return True


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('email')
    def _check_unique_customer_email(self):
        """
        Enforces case-insensitive email uniqueness across customers/contacts.
        Prevents duplicate customer registrations and email collisions.
        """
        for partner in self:
            if not partner.email:
                continue
            clean_email = validate_email_syntax(partner.email)
            # Case-insensitive duplicate check in PostgreSQL
            domain = [
                ('id', '!=', partner.id),
                ('email', '=ilike', clean_email),
            ]
            duplicate = self.search(domain, limit=1)
            if duplicate:
                raise ValidationError(
                    _("A customer or contact with the email '%s' already exists (Contact ID: %s, Name: %s). "
                      "Email addresses must be strictly unique (case-insensitive).") %
                    (clean_email, duplicate.id, duplicate.name)
                )


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.constrains('email')
    def _check_unique_user_email(self):
        """
        Enforces case-insensitive unique email validation on user accounts.
        """
        for user in self:
            if not user.email:
                continue
            clean_email = validate_email_syntax(user.email)
            domain = [
                ('id', '!=', user.id),
                ('email', '=ilike', clean_email),
            ]
            duplicate = self.search(domain, limit=1)
            if duplicate:
                raise ValidationError(
                    _("A user with the email '%s' already exists (User ID: %s, Login: %s). "
                      "User email must be strictly unique (case-insensitive).") %
                    (clean_email, duplicate.id, duplicate.login)
                )

    @api.constrains('password')
    def _check_password_policy(self):
        """
        Enforces password strength validation upon user password creation or update.
        """
        for user in self:
            # When password is set in vals/context
            if hasattr(user, 'password') and user.password:
                validate_password_strength(user.password)

    # ------------------------------------------------------------
    # ROLE MANAGEMENT & PRIVILEGE ESCALATION PREVENTION
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """
        Prevents privilege escalation:
        Only Subscription Administrators (group_subscription_manager) or Superusers
        can create Internal Staff (group_subscription_user) or Admin users.
        """
        staff_group = self.env.ref('subscription_management.group_subscription_user', raise_if_not_found=False)
        manager_group = self.env.ref('subscription_management.group_subscription_manager', raise_if_not_found=False)

        current_user = self.env.user
        is_admin = current_user.has_group('subscription_management.group_subscription_manager') or self.env.is_superuser()

        for vals in vals_list:
            # Check password if supplied during creation
            if vals.get('password'):
                validate_password_strength(vals['password'])

            # Normalize and validate email
            if vals.get('email'):
                vals['email'] = validate_email_syntax(vals['email'])
                # If login is identical or not set, normalize login too
                if not vals.get('login'):
                    vals['login'] = vals['email'].lower()

            # Inspect groups assigned to user
            groups_val = vals.get('groups_id') or []
            privileged_group_ids = set()
            if staff_group:
                privileged_group_ids.add(staff_group.id)
            if manager_group:
                privileged_group_ids.add(manager_group.id)

            assigned_group_ids = set()
            for cmd in groups_val:
                if isinstance(cmd, (list, tuple)):
                    if cmd[0] in (4,):  # (4, id)
                        assigned_group_ids.add(cmd[1])
                    elif cmd[0] in (6,):  # (6, 0, [ids])
                        assigned_group_ids.update(cmd[2])

            if privileged_group_ids.intersection(assigned_group_ids) and not is_admin:
                raise AccessError(
                    _("Security Violation: Only Subscription Administrators can create or grant Internal Staff accounts.")
                )

        return super(ResUsers, self).create(vals_list)

    def write(self, vals):
        """
        Guards role assignment on existing users:
        Non-admins cannot grant staff or manager permissions to anyone.
        """
        staff_group = self.env.ref('subscription_management.group_subscription_user', raise_if_not_found=False)
        manager_group = self.env.ref('subscription_management.group_subscription_manager', raise_if_not_found=False)

        current_user = self.env.user
        is_admin = current_user.has_group('subscription_management.group_subscription_manager') or self.env.is_superuser()

        if vals.get('password'):
            validate_password_strength(vals['password'])

        if vals.get('email'):
            vals['email'] = validate_email_syntax(vals['email'])

        if 'groups_id' in vals and not is_admin:
            privileged_group_ids = set()
            if staff_group:
                privileged_group_ids.add(staff_group.id)
            if manager_group:
                privileged_group_ids.add(manager_group.id)

            assigned_group_ids = set()
            for cmd in vals['groups_id']:
                if isinstance(cmd, (list, tuple)):
                    if cmd[0] in (4,):
                        assigned_group_ids.add(cmd[1])
                    elif cmd[0] in (6,):
                        assigned_group_ids.update(cmd[2])

            if privileged_group_ids.intersection(assigned_group_ids):
                raise AccessError(
                    _("Security Violation: Only Subscription Administrators can grant Internal Staff or Manager privileges.")
                )

        return super(ResUsers, self).write(vals)

    # ------------------------------------------------------------
    # PUBLIC API: CUSTOMER REGISTRATION & PASSWORD RESET
    # ------------------------------------------------------------

    @api.model
    def register_portal_customer(self, name, email, password, company_name=None):
        """
        Native customer registration method:
        - Validates email syntax and case-insensitive uniqueness
        - Validates password strength policy
        - Hashes password securely via Odoo's native user creation
        - Assigns customer role (group_subscription_portal)
        - Prevents privilege escalation
        """
        if not name or not name.strip():
            raise ValidationError(_("Customer name is required."))

        clean_email = validate_email_syntax(email).lower()
        validate_password_strength(password)

        # Check existing user
        existing_user = self.sudo().search([('email', '=ilike', clean_email)], limit=1)
        if existing_user:
            raise ValidationError(_("An account with the email '%s' is already registered.") % clean_email)

        # Check existing partner or create partner
        partner = self.env['res.partner'].sudo().search([('email', '=ilike', clean_email)], limit=1)
        if not partner:
            partner = self.env['res.partner'].sudo().create({
                'name': name.strip(),
                'email': clean_email,
                'company_type': 'company' if company_name else 'person',
                'customer_rank': 1,
            })

        # Fetch portal group
        portal_group = self.env.ref('subscription_management.group_subscription_portal', raise_if_not_found=False) \
            or self.env.ref('base.group_portal')

        # Create user account with portal customer group ONLY
        user = self.sudo().create({
            'name': name.strip(),
            'login': clean_email,
            'email': clean_email,
            'password': password,
            'partner_id': partner.id,
            'groups_id': [(6, 0, [portal_group.id])],
        })

        _logger.info("New portal customer registered successfully: %s (ID: %s)", clean_email, user.id)
        return {
            'success': True,
            'user_id': user.id,
            'partner_id': partner.id,
            'message': _("Customer registered successfully."),
        }

    @api.model
    def request_password_reset(self, email):
        """
        Native Password Reset by Registered Email:
        - Looks up account by case-insensitive email.
        - Dispatches native Odoo reset password instructions without exposing
          whether an arbitrary email is registered in the system (anti-enumeration defense).
        - Never exposes plaintext password information.
        """
        if not email or not isinstance(email, str):
            raise ValidationError(_("Email address is required for password reset."))

        clean_email = email.strip().lower()

        # Anti-enumeration message returned consistently
        generic_response = {
            'success': True,
            'message': _("If the email address '%s' is registered with Brightloop, "
                         "password reset instructions have been sent.") % clean_email
        }

        # Validate syntax
        try:
            validate_email_syntax(clean_email)
        except ValidationError:
            # Return same generic response or syntax error depending on strictness
            return generic_response

        user = self.sudo().search([('email', '=ilike', clean_email)], limit=1)
        if not user:
            # User not found, log internally and return generic message safely
            _logger.info("Password reset requested for non-existent email: %s", clean_email)
            return generic_response

        try:
            # Invoke Odoo's native password reset workflow
            user.action_reset_password()
            _logger.info("Password reset email successfully triggered for user: %s (ID: %s)", clean_email, user.id)
        except Exception as e:
            _logger.warning("Native password reset dispatch encountered: %s", str(e))

        return generic_response


class SubscriptionCustomerRegisterWizard(models.TransientModel):
    _name = 'subscription.customer.register.wizard'
    _description = 'Customer Registration Wizard'

    name = fields.Char(string="Customer Name", required=True)
    email = fields.Char(string="Email Address", required=True)
    company_name = fields.Char(string="Company / Organization")
    password = fields.Char(string="Initial Password", required=True)
    password_confirm = fields.Char(string="Confirm Password", required=True)

    def action_register(self):
        self.ensure_one()
        if self.password != self.password_confirm:
            raise ValidationError(_("Passwords do not match. Please re-enter both password fields identically."))
        res = self.env['res.users'].register_portal_customer(
            name=self.name,
            email=self.email,
            password=self.password,
            company_name=self.company_name
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Registration Successful"),
                'message': _("Customer account for %s (%s) has been successfully created.") % (self.name, self.email),
                'type': 'success',
                'sticky': False,
            }
        }
