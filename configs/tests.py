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

        # 3. User checks wheel info — response is now a list of campaigns
        self.client.force_authenticate(user=self.customer_user)
        wheel_res = self.client.get("/api/v1/user/user/spin-to-win/wheel")
        self.assertEqual(wheel_res.status_code, status.HTTP_200_OK)
        wheel_data = wheel_res.json()
        self.assertIn("campaigns", wheel_data)
        campaigns_list = wheel_data["campaigns"]
        self.assertEqual(len(campaigns_list), 1)
        campaign_entry = campaigns_list[0]
        self.assertEqual(campaign_entry["campaign_id"], campaign_id)
        self.assertEqual(len(campaign_entry["slices"]), 2)

        # 4. Spin without campaign_id must return 400
        no_id_res = self.client.post("/api/v1/user/user/spin-to-win/spin", {})
        self.assertEqual(no_id_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("campaign_id", no_id_res.json().get("error", ""))

        # 5. User performs 1st spin (campaign total spins = 1 < min 3 threshold)
        spin1_res = self.client.post("/api/v1/user/user/spin-to-win/spin", {"campaign_id": campaign_id})
        self.assertEqual(spin1_res.status_code, status.HTTP_201_CREATED)
        spin1_data = spin1_res.json()
        self.assertEqual(spin1_data["title"], "Try Again")
        self.assertFalse(spin1_data["is_win"])

        # 6. Perform 2nd spin (total spins = 2 < 3)
        spin2_res = self.client.post("/api/v1/user/user/spin-to-win/spin", {"campaign_id": campaign_id})
        self.assertEqual(spin2_res.status_code, status.HTTP_201_CREATED)

        # 7. Perform 3rd spin (total spins = 3 >= 3 threshold -> 50% OFF becomes eligible!)
        from unittest.mock import patch
        item2_obj = SpinToWinItem.objects.get(pk=item2_res.json()["id"])
        with patch("random.choices", return_value=[item2_obj]):
            spin3_res = self.client.post("/api/v1/user/user/spin-to-win/spin", {"campaign_id": campaign_id})
            self.assertEqual(spin3_res.status_code, status.HTTP_201_CREATED)
            spin3_data = spin3_res.json()
            self.assertTrue(spin3_data["is_win"])
            self.assertEqual(spin3_data["title"], "50% OFF Promo Code")
            self.assertIn("MEGA50", spin3_data["promo_code"])

        # 8. Check User My Prizes
        prizes_res = self.client.get("/api/v1/user/user/spin-to-win/my-prizes")
        self.assertEqual(prizes_res.status_code, status.HTTP_200_OK)
        prizes_json = prizes_res.json()
        prizes = prizes_json.get("results", prizes_json)
        self.assertEqual(len(prizes), 1)
        self.assertIn("MEGA50", prizes[0]["promo_code"])

    def test_multiple_simultaneous_active_campaigns(self):
        """Wheel endpoint returns all active campaigns; spin targets a specific one by campaign_id."""
        self.client.force_authenticate(user=self.admin_user)

        # Create two active campaigns
        camp1_res = self.client.post("/api/v1/admin/admin/spin-to-win/campaigns", {
            "title": "Weekend Wheel",
            "is_active": True,
            "max_spins_per_user_per_day": 2,
        })
        self.assertEqual(camp1_res.status_code, status.HTTP_201_CREATED)
        camp1_id = camp1_res.json()["id"]

        camp2_res = self.client.post("/api/v1/admin/admin/spin-to-win/campaigns", {
            "title": "VIP Spinner",
            "is_active": True,
            "max_spins_per_user_per_day": 1,
        })
        self.assertEqual(camp2_res.status_code, status.HTTP_201_CREATED)
        camp2_id = camp2_res.json()["id"]

        # Add a slice to each campaign
        self.client.post("/api/v1/admin/admin/spin-to-win/items", {
            "campaign": camp1_id, "title": "Try Again", "item_type": "empty",
            "probability_weight": 1, "slice_index": 0, "is_active": True,
        })
        self.client.post("/api/v1/admin/admin/spin-to-win/items", {
            "campaign": camp2_id, "title": "VIP Prize", "item_type": "promocode",
            "promo_code_value": "VIP10OFF", "probability_weight": 1, "slice_index": 0, "is_active": True,
        })

        # Wheel must return both campaigns
        self.client.force_authenticate(user=self.customer_user)
        wheel_res = self.client.get("/api/v1/user/user/spin-to-win/wheel")
        self.assertEqual(wheel_res.status_code, status.HTTP_200_OK)
        campaigns_list = wheel_res.json()["campaigns"]
        self.assertEqual(len(campaigns_list), 2)
        returned_ids = {c["campaign_id"] for c in campaigns_list}
        self.assertIn(camp1_id, returned_ids)
        self.assertIn(camp2_id, returned_ids)

        # Spinning with an inactive/non-existent campaign_id returns 400
        bad_spin = self.client.post("/api/v1/user/user/spin-to-win/spin", {"campaign_id": 99999})
        self.assertEqual(bad_spin.status_code, status.HTTP_400_BAD_REQUEST)

        # Spin against camp2 specifically
        spin_res = self.client.post("/api/v1/user/user/spin-to-win/spin", {"campaign_id": camp2_id})
        self.assertEqual(spin_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(spin_res.json()["title"], "VIP Prize")

        # Deactivate camp1 — wheel should now return only camp2
        self.client.force_authenticate(user=self.admin_user)
        self.client.patch(f"/api/v1/admin/admin/spin-to-win/campaigns/{camp1_id}", {"is_active": False})
        self.client.force_authenticate(user=self.customer_user)
        wheel_res2 = self.client.get("/api/v1/user/user/spin-to-win/wheel")
        campaigns_list2 = wheel_res2.json()["campaigns"]
        self.assertEqual(len(campaigns_list2), 1)
        self.assertEqual(campaigns_list2[0]["campaign_id"], camp2_id)

    def test_empty_campaign_does_not_expose_other_campaign_slices(self):
        """A new active campaign with no slices must not leak previous campaign items."""
        self.client.force_authenticate(user=self.admin_user)

        old_res = self.client.post("/api/v1/admin/admin/spin-to-win/campaigns", {
            "title": "Existing Wheel",
            "is_active": True,
            "max_spins_per_user_per_day": 1,
        })
        self.assertEqual(old_res.status_code, status.HTTP_201_CREATED)
        old_id = old_res.json()["id"]

        self.client.post("/api/v1/admin/admin/spin-to-win/items", {
            "campaign": old_id, "title": "yele", "item_type": "discount",
            "promo_code_value": "6996", "probability_weight": 10, "slice_index": 2,
            "is_active": True,
        })
        self.client.post("/api/v1/admin/admin/spin-to-win/items", {
            "campaign": old_id, "title": "bkl", "item_type": "empty",
            "probability_weight": 10, "slice_index": 1, "is_active": True,
        })

        new_res = self.client.post("/api/v1/admin/admin/spin-to-win/campaigns", {
            "title": "Empty New Wheel",
            "is_active": True,
            "max_spins_per_user_per_day": 1,
        })
        self.assertEqual(new_res.status_code, status.HTTP_201_CREATED)
        new_id = new_res.json()["id"]
        self.assertEqual(new_res.json().get("items") or [], [])

        # Admin campaign-by-id stays scoped to that campaign
        detail_res = self.client.get(f"/api/v1/admin/admin/spin-to-win/campaigns/{new_id}")
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.json()["items"], [])

        # Admin items list must filter by campaign instead of returning every slice
        filtered_res = self.client.get("/api/v1/admin/admin/spin-to-win/items", {"campaign": new_id})
        self.assertEqual(filtered_res.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered_res.json()["count"], 0)
        self.assertEqual(filtered_res.json()["results"], [])

        old_items_res = self.client.get("/api/v1/admin/admin/spin-to-win/items", {"campaign": old_id})
        self.assertEqual(old_items_res.json()["count"], 2)
        self.assertTrue(all(item["campaign"] == old_id for item in old_items_res.json()["results"]))

        # Wheel omits the empty campaign; remaining slices stay on the old campaign_id
        self.client.force_authenticate(user=self.customer_user)
        wheel_res = self.client.get("/api/v1/user/user/spin-to-win/wheel")
        self.assertEqual(wheel_res.status_code, status.HTTP_200_OK)
        campaigns_list = wheel_res.json()["campaigns"]
        returned_ids = {c["campaign_id"] for c in campaigns_list}
        self.assertNotIn(new_id, returned_ids)
        self.assertIn(old_id, returned_ids)

        old_entry = next(c for c in campaigns_list if c["campaign_id"] == old_id)
        self.assertEqual(len(old_entry["slices"]), 2)
        self.assertTrue(all(slice_item["campaign"] == old_id for slice_item in old_entry["slices"]))
