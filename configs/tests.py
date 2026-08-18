from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User, UserProfile
from configs.models import SpinToWinCampaign, SpinToWinItem
from core.models import Banner


class AdminPanelAndSpinToWinTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Superuser / Super Admin
        self.admin_user = User.objects.create_superuser(
            username="adminuser",
            email="admin@example.com",
            password="adminpassword"
        )
        UserProfile.objects.create(user=self.admin_user, role=UserProfile.ROLE_ADMIN)

        # Standard Customer User
        self.customer_user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="customerpassword"
        )
        UserProfile.objects.create(user=self.customer_user, role=UserProfile.ROLE_CUSTOMER)

    def test_super_admin_login_payload(self):
        url = "/user/api/users/login"
        response = self.client.post(url, {
            "email": "admin@example.com",
            "password": "adminpassword"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data.get("is_admin"))
        self.assertTrue(data.get("is_superuser"))
        self.assertEqual(data.get("role"), "admin")

    def test_admin_banner_crud_and_user_banner_list(self):
        self.client.force_authenticate(user=self.admin_user)

        create_res = self.client.post("/api/v1/admin/admin/banners", {
            "title": "Summer Discount Promo",
            "body": "Get up to 50% off",
            "cta_url": "https://example.com/deals",
            "priority": 1,
            "is_visible": True,
        })
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        banner_id = create_res.json()["id"]
        self.assertEqual(create_res.json().get("cta_url"), "https://example.com/deals")
        self.assertTrue(Banner.objects.filter(pk=banner_id).exists())

        toggle_res = self.client.post(f"/api/v1/admin/admin/banners/{banner_id}/toggle-visible")
        self.assertEqual(toggle_res.status_code, status.HTTP_200_OK)
        self.assertFalse(toggle_res.json()["is_visible"])

        self.client.post(f"/api/v1/admin/admin/banners/{banner_id}/toggle-visible")

        self.client.force_authenticate(user=None)
        user_banners_res = self.client.get("/user/api/core/banners")
        self.assertEqual(user_banners_res.status_code, status.HTTP_200_OK)
        banners_data = user_banners_res.json()
        banners_list = banners_data.get("results", banners_data)
        self.assertEqual(len(banners_list), 1)
        self.assertEqual(banners_list[0]["title"], "Summer Discount Promo")
        self.assertEqual(banners_list[0]["cta_url"], "https://example.com/deals")

        # Duplicate AppBanner endpoint must be gone
        old_user_banners = self.client.get("/api/v1/user/user/banners")
        self.assertEqual(old_user_banners.status_code, status.HTTP_404_NOT_FOUND)

        # Customers cannot write banners
        self.client.force_authenticate(user=self.customer_user)
        forbidden = self.client.post("/api/v1/admin/admin/banners", {"title": "Nope"})
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_spin_to_win_campaign_items_and_spin_mechanics(self):
        self.client.force_authenticate(user=self.admin_user)

        # 1. Create Spin to Win Campaign
        campaign_res = self.client.post("/api/v1/admin/admin/spin-to-win/campaigns", {
            "title": "Mega Rewards Wheel",
            "description": "Spin and win awesome promo codes",
            "is_active": True,
            "max_spins_per_user_per_day": 5
        })
        self.assertEqual(campaign_res.status_code, status.HTTP_201_CREATED)
        campaign_id = campaign_res.json()["id"]

        # 2. Create Items / Wheel Slices
        # Item 1: Try Again (empty)
        self.client.post("/api/v1/admin/admin/spin-to-win/items", {
            "campaign": campaign_id,
            "title": "Try Again",
            "item_type": "empty",
            "promo_code_value": "Better luck next time!",
            "min_spins_before_win": 0,
            "probability_weight": 5,
            "slice_index": 0,
            "is_active": True
        })

        # Item 2: High tier promo code text requiring min_spins_before_win = 3
        item2_res = self.client.post("/api/v1/admin/admin/spin-to-win/items", {
            "campaign": campaign_id,
            "title": "50% OFF Promo Code",
            "item_type": "promocode",
            "promo_code_value": "Use promo code MEGA50 to get 50% OFF your next meal!",
            "min_spins_before_win": 3,
            "stock_limit": 10,
            "probability_weight": 10,
            "slice_index": 1,
            "is_active": True
        })
        self.assertEqual(item2_res.status_code, status.HTTP_201_CREATED)

        # 3. User checks wheel info
        self.client.force_authenticate(user=self.customer_user)
        wheel_res = self.client.get("/api/v1/user/user/spin-to-win/wheel")
        self.assertEqual(wheel_res.status_code, status.HTTP_200_OK)
        wheel_data = wheel_res.json()
        self.assertTrue(wheel_data["is_active"])
        self.assertEqual(len(wheel_data["slices"]), 2)

        # 4. User performs 1st spin (campaign total spins = 1 < min 3 threshold)
        spin1_res = self.client.post("/api/v1/user/user/spin-to-win/spin")
        self.assertEqual(spin1_res.status_code, status.HTTP_201_CREATED)
        spin1_data = spin1_res.json()
        self.assertEqual(spin1_data["title"], "Try Again")
        self.assertFalse(spin1_data["is_win"])

        # 5. Perform 2nd spin (total spins = 2 < 3)
        spin2_res = self.client.post("/api/v1/user/user/spin-to-win/spin")
        self.assertEqual(spin2_res.status_code, status.HTTP_201_CREATED)

        # 6. Perform 3rd spin (total spins = 3 >= 3 threshold -> 50% OFF becomes eligible!)
        from unittest.mock import patch
        item2_obj = SpinToWinItem.objects.get(pk=item2_res.json()["id"])
        with patch("random.choices", return_value=[item2_obj]):
            spin3_res = self.client.post("/api/v1/user/user/spin-to-win/spin")
            self.assertEqual(spin3_res.status_code, status.HTTP_201_CREATED)
            spin3_data = spin3_res.json()
            self.assertTrue(spin3_data["is_win"])
            self.assertEqual(spin3_data["title"], "50% OFF Promo Code")
            self.assertIn("MEGA50", spin3_data["promo_code"])

        # 7. Check User My Prizes
        prizes_res = self.client.get("/api/v1/user/user/spin-to-win/my-prizes")
        self.assertEqual(prizes_res.status_code, status.HTTP_200_OK)
        prizes_json = prizes_res.json()
        prizes = prizes_json.get("results", prizes_json)
        self.assertEqual(len(prizes), 1)
        self.assertIn("MEGA50", prizes[0]["promo_code"])

