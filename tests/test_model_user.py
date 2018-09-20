import time
from flask import url_for
from tests.base_test_client import FlaskTestClient
from app.user.models.user import User, Role, load_user
from app.user.models.app_group import AppGroup
from app.fhir.models.email_address import EmailAddress
from app.fhir.models.phone_number import PhoneNumber
from app.fhir.models.address import Address
from app.auth.security import app_group_dict
from app.extensions import db

user_dict = dict(email="john.doe@example.com",
                 username="john.doe",
                 password="testpw",
                 first_name="john",
                 last_name="doe",
                 phone_number='123456789',
                 confirmed=True)


def create_test_user(username=user_dict.get("username"), email=user_dict.get("email"),
                     password=user_dict.get("password"), confirmed=user_dict.get("confirmed"),
                     first_name=user_dict.get("first_name"), last_name=user_dict.get("last_name"),
                     phone_number=user_dict.get("phone_number")):
    """Quickly create a test user for use in unittests"""
    return User(username=username, password=password, confirmed=confirmed, first_name=first_name,
                last_name=last_name, email=email, phone_number=phone_number)


class UserModelSecurityTestCase(FlaskTestClient):
    """Unittests related to user authentication and security"""

    def test_password_setter(self):
        """Test password hash is populated"""
        u = User(password='cat')
        self.assertTrue(u.password_hash is not None)

    def test_password_verification(self):
        """Test password hash verification with known password"""
        u = User(password='cat')
        self.assertTrue(u.verify_password('cat'))
        self.assertFalse(u.verify_password('dog'))

    def test_password_salts_are_random(self):
        """Test password is stored as salted hash with userid as salt source"""
        u = User(password='cat')
        u2 = User(password='cat')
        self.assertTrue(u.password_hash != u2.password_hash)

    def test_last_password_is_saved(self):
        """Test that old password is stored and can be verified on password change"""
        u = User(password='cat')
        self.assertTrue(u.verify_password('cat'))
        u.password = 'dog'
        self.assertTrue(u.verify_password('dog'))
        self.assertTrue(u.verify_last_password('cat'))

    def test_valid_confirmation_token(self):
        """Check that confirmation token processes in the User model"""
        u = User(password='cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_confirmation_token()
        self.assertTrue(u.confirm(token))

    def test_invalid_confirmation_token(self):
        """Test an invalid confirmation token, confirm it cannot be used to confirm the wrong user
        """
        u1 = User(password='cat')
        u2 = User(password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_confirmation_token()
        self.assertFalse(u2.confirm(token))

    def test_expired_confirmation_token(self):
        """Test expired confirmation token, confirm it cannot be used to confirm user"""
        u = User(password='cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_confirmation_token(1)
        time.sleep(2)
        self.assertFalse(u.confirm(token))

    def test_valid_reset_token(self):
        """Test a valid password reset token is accepted"""
        u = User(password='cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_reset_token()
        self.assertTrue(u.reset_password(token, 'dog'))  # Test token value matches userid
        self.assertTrue(u.verify_password('dog'))  # Test new password is dog

    def test_invalid_reset_token(self):
        """Test that an invalid password reset token is not accepted"""
        u1 = User(password='cat')
        u2 = User(password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_reset_token()
        none_token = None
        self.assertFalse(u2.reset_password(token, 'horse'))
        self.assertFalse(u2.reset_password(none_token, 'horse'))
        self.assertTrue(u2.verify_password('dog'))


class UserModelLoadCreateTestCase(FlaskTestClient):
    """Unittests related to loading and creating User records"""

    def test_users_created_in_db(self):
        """When we add a user, does it actually exist in the database?"""
        u = User()
        db.session.add(u)
        db.session.commit()
        userlist = User.query.all()
        self.assertEqual(len(userlist), 1)

    def test_load_user(self):
        """Test userloader returns a user record"""
        u = User(username='testuser')
        db.session.add(u)
        db.session.commit()
        u2 = load_user(u.id)
        self.assertIs(u, u2)


class UserModelRandomizationTestCase(FlaskTestClient):
    """Unittests related to randomization of user records"""

    def test_randomize_user(self):
        """Test creation of random user records"""
        user = User()
        user.randomize_user()
        db.session.add(user)
        self.assertTrue(user is not None)
        self.assertTrue(user.email is not None)
        self.assertTrue(user.phone_number.number is not None)
        self.assertTrue(user.first_name is not None)
        self.assertTrue(user.last_name is not None)
        self.assertTrue(user.dob is not None)
        self.assertTrue(user.active)
        self.assertFalse(user.confirmed)
        self.assertEqual(user.role.name, 'User')


class UserRoleTestCase(FlaskTestClient):
    """Unittests related to creating and assigning Roles to Users"""

    def test_initialize_roles_staticmethod(self):
        """Confirm roles are initialized"""
        Role.initialize_roles()
        admin_role = Role.query.filter_by(name='Admin').first()
        super_admin_role = Role.query.filter_by(name='Super Admin').first()
        user_role = Role.query.filter_by(name='User').first()
        self.assertTrue(admin_role is not None)
        self.assertTrue(super_admin_role is not None)
        self.assertTrue(user_role is not None)

    def test_init_role_assign_integer(self):
        """
        Test assigning role on User initialization
        --Allow for integer role_id on init
        """
        u = User(username=user_dict.get('username'), role=1)
        db.session.add(u)
        self.assertIsInstance(u.role, Role)
        self.assertEqual(u.role.id, 1, 'Role id integer not processed during User init')
        db.session.delete(u)

        bad_id = Role.query.order_by(Role.id.desc()).first().id + 1
        u = User(username=user_dict.get('username'), role=bad_id)
        db.session.add(u)
        self.assertIs(u.role, Role.query.filter_by(default=True).first(), 'Default role not assigned to User')
        self.assertNotEqual(u.role.id, bad_id, 'Default role not assigned to User')

    def test_init_role_assign_role_object(self):
        """Test assigning role on User initialization"""
        role = Role.query.filter_by(default=False).first()
        u = User(username=user_dict.get('username'), role=role)
        db.session.add(u)
        self.assertIs(u.role, role, 'Could not assign Role object to User during init')

    def test_init_role_assign_default(self):
        """Test assigning role on User initialization -Confirm default Role is assigned"""
        u = User(username=user_dict.get('username'), role=None)
        db.session.add(u)
        self.assertIs(u.role, Role.query.filter_by(default=True).first(), 'Default role not assigned')


class UserAppGroupTestCase(FlaskTestClient):
    """Unittests related to creating and assigning AppGroups for Users"""

    def test_initialize_app_groups_staticmethod(self):
        """Test AppGroup.initialize_app_groups() to ensure app_group records are created as expected"""
        # Note: AppGroup initialization completed in SetUp
        ag_names = {x.name for x in AppGroup.query.all()}
        self.assertIsNotNone(ag_names, 'ApGroups not initialized')
        expected_names = {x for x in app_group_dict}
        self.assertEqual(ag_names, expected_names, 'AppGroups created do not match expected')

    def test_init_appgroup_assign_integer(self):
        """Test assigning app_groups on User initialization"""
        u = User(username=user_dict.get('username'), app_group=1)
        db.session.add(u)
        self.assertIsInstance(u.app_groups[0], AppGroup)
        self.assertEqual(u.app_groups[0].id, 1, 'AppGroup id integer not processed during User init')
        db.session.delete(u)

    def test_init_appgroup_assign_bad_integer(self):
        """Test assigning app_group with bad integer id on User initialization"""
        bad_id = AppGroup.query.order_by(AppGroup.id.desc()).first().id + 1
        u = User(username=user_dict.get('username'), app_group=bad_id)
        db.session.add(u)
        self.assertIs(u.app_groups[0], AppGroup.query.filter_by(default=True).first(),
                      'Default app-group not assigned to User')
        self.assertNotEqual(u.app_groups[0].id, bad_id, 'Default app-group not assigned to User')

    def test_init_appgroup_assign_object(self):
        """
        Test assigning app_groups on User initialization
        --Allow for passing SQLAlchemy AppGroup object on init
        """
        appgroup = AppGroup.query.filter_by(default=False).first()
        u = User(username=user_dict.get('username'), app_group=appgroup)
        db.session.add(u)
        self.assertIs(u.app_groups[0], appgroup, 'Could not assign AppGroup object to User during init')

    def test_init_appgroup_assign_default(self):
        """
        Test assigning app_groups on User initialization
        --Confirm default AppGroup is assigned
        """
        u = User(username=user_dict.get('username'), app_group=None)
        db.session.add(u)
        self.assertIs(u.app_groups[0], AppGroup.query.filter_by(default=True).first(), 'Default appgroup not assigned')


class UserModelDemographicTestCase(FlaskTestClient):
    """Unittests related to setting and reading user demographic attributes"""

    def test_init_email_assign(self):
        """Test email property and email assignment on initialization of object"""
        u = create_test_user()
        db.session.add(u)
        db.session.commit()
        self.assertIsInstance(u.email_addresses[0], EmailAddress)
        self.assertIsInstance(u.email, EmailAddress)
        self.assertEqual(user_dict.get('email'), u.email.email)

    def test_init_phone_number_assign(self):
        """Test phone_number property and phone_number assignment on initialization of object"""
        u = create_test_user()
        db.session.add(u)
        db.session.commit()
        self.assertIsInstance(u.phone_numbers[0], PhoneNumber)
        self.assertIsInstance(u.phone_number, PhoneNumber)
        self.assertEqual(u.phone_number.number, user_dict.get('phone_number'))
        self.assertEqual(u.phone_number.type, 'MOBILE')

    def test_address_assign(self):
        """Test assigning an address to a user.  Test the property that fetches active and primary address"""
        u = create_test_user()
        a = Address(address1='123 Main Street', city='Anytown', state='WI', primary=True, active=True)
        u.addresses.append(a)
        db.session.add(u)
        db.session.commit()
        self.assertIsInstance(u.addresses[0], Address)
        self.assertIsInstance(u.address, Address)
        self.assertIs(u.address, a)
        a.primary = False  # Now the address property should return None
        db.session.add(a)
        db.session.commit()
        self.assertIsNone(u.address, Address)

    def test_user_resource_url(self):
        """Test that user resource API url is constructed appropriately for User model"""
        u = create_test_user()
        db.session.add(u)
        db.session.commit()
        self.assertIsNotNone(u.get_url())
        self.assertEqual(u.get_url(), url_for('user.get_user', userid=u.id, _external=True))
