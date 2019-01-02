"""Utility for invoking the SmartThings Cloud API."""

from typing import Optional

from aiohttp import ClientSession
import requests

from . import errors
from .errors import APIResponseError

API_BASE = "https://api.smartthings.com/v1/"
API_LOCATIONS = "locations"
API_LOCATION = API_LOCATIONS + "/{location_id}"
API_DEVICES = "devices"
API_DEVICE = API_DEVICES + "/{device_id}"
API_DEVICE_STATUS = "devices/{device_id}/status"
API_DEVICE_COMMAND = "devices/{device_id}/commands"
API_APPS = "apps"
API_APP = "apps/{app_id}"
API_APP_OAUTH = "apps/{app_id}/oauth"
API_APP_SETTINGS = "apps/{app_id}/settings"
API_INSTALLEDAPPS = "installedapps"
API_INSTALLEDAPP = "installedapps/{installed_app_id}"
API_SUBSCRIPTIONS = API_INSTALLEDAPP + "/subscriptions"
API_SUBSCRIPTION = API_SUBSCRIPTIONS + "/{subscription_id}"


class Api:
    """
    Wrapper around the SmartThings Cloud API operations.

    https://smartthings.developer.samsung.com/docs/api-ref/st-api.html
    """

    def __init__(self, session: ClientSession, token: str, *,
                 api_base: str = API_BASE):
        """Create a new API with the given session and token."""
        self._session = session
        self._token = token
        self._api_base = api_base

    async def get_locations(self) -> dict:
        """
        Get locations.

        https://smartthings.developer.samsung.com/docs/api-ref/st-api.html#operation/listLocations
        """
        return await self.get_items(API_LOCATIONS)

    async def get_location(self, location_id: str) -> dict:
        """
        Get a specific location.

        https://smartthings.developer.samsung.com/docs/api-ref/st-api.html#operation/getLocation
        """
        return await self.get(API_LOCATION.format(location_id=location_id))

    @property
    def session(self) -> ClientSession:
        """Get the instance of the session."""
        return self._session

    @session.setter
    def session(self, value: ClientSession):
        """Set the instance of the session."""
        self._session = value

    @property
    def token(self):
        """Get the token used when making requests."""
        return self._token

    @token.setter
    def token(self, value):
        """Set the token to use when making requests."""
        self._token = value

    async def request(self, method: str, url: str, params: dict = None,
                      data: dict = None):
        """Perform a request against the specified parameters."""
        async with self._session.request(
                method, url, params=params, json=data,
                headers={"Authorization": "Bearer " + self._token}) as resp:
            if resp.status == 200:
                return await resp.json()
            if resp.status in (400, 422, 429, 500):
                data = None
                try:
                    data = await resp.json()
                except Exception:  # pylint: disable=broad-except
                    pass
                raise APIResponseError(
                    resp.request_info,
                    resp.history,
                    status=resp.status,
                    message=resp.reason,
                    headers=resp.headers,
                    data=data)
            resp.raise_for_status()

    async def get(self, resource: str, *, params: dict = None):
        """Get a resource."""
        return await self.request('get', self._api_base + resource, params)

    async def get_items(self, resource: str, *, params: dict = None):
        """Perform requests for a list of items that may have pages."""
        resp = await self.request('get', self._api_base + resource, params, None)
        items = resp.get('items', [])
        next_link = Api._get_next_link(resp)
        while next_link:
            resp = await self.request('get', next_link, params, None)
            items.extend(resp.get('items', []))
            next_link = Api._get_next_link(resp)
        return items

    @staticmethod
    def _get_next_link(data):
        links = data.get('_links')
        if not links:
            return None
        next_link = links.get('next')
        if not next_link:
            return None
        return next_link.get('href')


class api_old:  # pylint: disable=invalid-name
    """
    Utility for invoking the SmartThings Cloud API.

    https://smartthings.developer.samsung.com/docs/api-ref/st-api.html
    """

    def __init__(self, token: str):
        """Initialize a new instance of the API class."""
        self._headers = {"Authorization": "Bearer " + token}

    def get_devices(self, params: Optional[dict] = None) -> dict:
        """
        Get the device definitions.

        https://smartthings.developer.samsung.com/docs/api-ref/st-api.html#operation/getDevices
        """
        return self._request_paged_list('get', API_DEVICES, params=params)

    def get_device(self, device_id: str) -> dict:
        """
        Get as specific device.

        https://smartthings.developer.samsung.com/docs/api-ref/st-api.html#operation/getDevice
        """
        return self._request(
            'get', API_DEVICE.format(device_id=device_id))

    def get_device_status(self, device_id: str) -> dict:
        """Get the status of a specific device."""
        return self._request(
            'get',
            API_DEVICE_STATUS.format(device_id=device_id))

    def post_command(self, device_id, capability, command, args,
                     component="main") -> object:
        """
        Execute commands on a device.

        https://smartthings.developer.samsung.com/docs/api-ref/st-api.html#operation/executeDeviceCommands
        """
        data = {
            "commands": [
                {
                    "component": component,
                    "capability": capability,
                    "command": command
                }
            ]
        }
        if args:
            data["commands"][0]["arguments"] = args

        return self._request(
            'post',
            API_DEVICE_COMMAND.format(device_id=device_id),
            data)

    def get_apps(self) -> dict:
        """
        Get list of apps.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/listApps
        """
        return self._request_paged_list('get', API_APPS)

    def get_app(self, app_id: str) -> dict:
        """
        Get the details of the specific app.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/getApp
        """
        return self._request(
            'get',
            API_APP.format(app_id=app_id))

    def create_app(self, data: dict) -> dict:
        """
        Create a new app.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/createApp
        """
        return self._request('post', API_APPS, data)

    def update_app(self, app_id: str, data: dict) -> dict:
        """
        Update an existing app.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/updateApp
        """
        return self._request(
            'put', API_APP.format(app_id=app_id), data)

    def delete_app(self, app_id: str):
        """
        Delete an app.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/deleteApp
        """
        return self._request(
            'delete', API_APP.format(app_id=app_id))

    def get_app_settings(self, app_id: str) -> dict:
        """
        Get an app's settings.

        https://smartthings.developer.samsung.com/docs/api-ref/st-api.html#operation/getAppSettings
        """
        return self._request('get', API_APP_SETTINGS.format(app_id=app_id))

    def update_app_settings(self, app_id: str, data: dict) -> dict:
        """
        Update an app's settings.

        https://smartthings.developer.samsung.com/docs/api-ref/st-api.html#operation/updateAppSettings
        """
        return self._request(
            'put', API_APP_SETTINGS.format(app_id=app_id), data)

    def get_app_oauth(self, app_id: str) -> dict:
        """
        Get an app's oauth settings.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/getAppOauth
        """
        return self._request('get', API_APP_OAUTH.format(app_id=app_id))

    def update_app_oauth(self, app_id: str, data: dict) -> dict:
        """
        Update an app's oauth settings.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/updateAppOauth
        """
        return self._request(
            'put', API_APP_OAUTH.format(app_id=app_id), data)

    def get_installedapps(self) -> dict:
        """
        Get list of installedapps.

        https://smartthings.developer.samsung.com/docs/api-ref/st-api.html#operation/listInstallations
        """
        return self._request_paged_list('get', API_INSTALLEDAPPS)

    def get_installedapp(self, installed_app_id: str) -> dict:
        """
        Get the details of the specific installedapp.

        https://smartthings.developer.samsung.com/docs/api-ref/st-api.html#operation/getInstallation
        """
        return self._request(
            'get',
            API_INSTALLEDAPP.format(installed_app_id=installed_app_id))

    def delete_installedapp(self, installed_app_id: str):
        """
        Delete an app.

        https://smartthings.developer.samsung.com/docs/api-ref/st-api.html#operation/deleteInstallation
        """
        return self._request(
            'delete', API_INSTALLEDAPP.format(
                installed_app_id=installed_app_id))

    def get_subscriptions(self, installed_app_id: str) -> dict:
        """
        Get installedapp's subscriptions.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/listSubscriptions
        """
        return self._request_paged_list(
            'get',
            API_SUBSCRIPTIONS.format(installed_app_id=installed_app_id))

    def create_subscription(self, installed_app_id: str, data: dict) -> dict:
        """
        Create a subscription for an installedapp.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/saveSubscription
        """
        return self._request(
            'post',
            API_SUBSCRIPTIONS.format(installed_app_id=installed_app_id),
            data)

    def delete_all_subscriptions(self, installed_app_id: str) -> dict:
        """
        Delete all subscriptions for an installedapp.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/deleteAllSubscriptions
        """
        return self._request(
            'delete',
            API_SUBSCRIPTIONS.format(installed_app_id=installed_app_id))

    def get_subscription(self, installed_app_id: str, subscription_id: str) \
            -> dict:
        """
        Get an individual subscription.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/getSubscription
        """
        return self._request(
            'get',
            API_SUBSCRIPTION.format(
                installed_app_id=installed_app_id,
                subscription_id=subscription_id))

    def delete_subscription(self, installed_app_id: str, subscription_id: str):
        """
        Delete an individual subscription.

        https://smartthings.developer.samsung.com/develop/api-ref/st-api.html#operation/deleteSubscription
        """
        return self._request(
            'delete',
            API_SUBSCRIPTION.format(
                installed_app_id=installed_app_id,
                subscription_id=subscription_id))

    @staticmethod
    def _get_next_link(data):
        links = data.get('_links')
        if not links:
            return None
        next_link = links.get('next')
        if not next_link:
            return None
        return next_link.get('href')

    def _request_paged_list(self, method: str, resource: str,
                            data: dict = None, params: dict = None):
        response = self._request(method, resource, data, params)
        items = response['items']
        next_link = api_old._get_next_link(response)
        while next_link:
            response = self._request(method, data=data, params=params,
                                     url=next_link)
            items.extend(response['items'])
            next_link = api_old._get_next_link(response)
        return {'items': items}

    def _request(self, method: str, resource: str = None, data: dict = None,
                 params: dict = None, *, url: str = None):
        response = requests.request(
            method,
            url if url else API_BASE + resource,
            params=params,
            json=data,
            headers=self._headers)

        if response.ok:
            return response.json()
        if response.status_code == 401:
            raise errors.APIUnauthorizedError
        elif response.status_code == 403:
            raise errors.APIForbiddenError
        raise errors.APIUnknownError
