import kivy
from enum import Enum


# Important!
# add all required permissions here
class PERMISSION_ENUM(Enum):
    CAMERA = "CAMERA"


class PermissionManager:
    def __init__(self, myPermissions: list[PERMISSION_ENUM] = None):
        # If no myPermissions list is specified, all permissions in MyPermissionEnum will be loaded

        self.platform = kivy.platform
        self.isAndroid = self.platform == "android"

        self.myPermissions = (
            [p for p in PERMISSION_ENUM] if myPermissions == None else myPermissions
        )

        # skip rest of setup
        if not self.isAndroid:
            return

        # from android.runnable import (  # pylint: disable=import-error # type: ignore
        #     run_on_ui_thread,
        # )
        from android.permissions import (  # pylint: disable=import-error # type: ignore
            request_permissions,
            Permission,
            check_permission,
        )

        self._native_Permission = Permission
        self._native_check_permission = check_permission
        self._native_request_permissions = request_permissions

    def _generate_cannot_call_method_message(self):
        return f"Cannot call this method on platform other than android. Current platform: {self.platform}"

    def _skipping_permissions_message(self, myPermissions: list[PERMISSION_ENUM]):
        permissionNames = [p.value for p in myPermissions]
        return f"Skipping permissions check since platform is {self.platform} and not android. The following permissions were requested: {permissionNames}"

    def _myPermissionToNative(self, myPermission: PERMISSION_ENUM):
        if not self.isAndroid:
            raise Exception(self._generate_cannot_call_method_message())

        return getattr(self._native_Permission, myPermission.value, None)

    def _myPermissionsToNative(self, myPermissions: list[PERMISSION_ENUM]):
        nativePermissions = [self._myPermissionToNative(p) for p in myPermissions]
        if not all(nativePermissions):
            raise Exception("One or more permissions is invalid:", myPermissions)
        
        return nativePermissions


    def requestPermissions(self, myPermissions: list[PERMISSION_ENUM] = []):
        if not myPermissions:
            myPermissions = self.myPermissions

        if not self.isAndroid:
            print(self._skipping_permissions_message(myPermissions))
            return

        permissionNames = [p.value for p in myPermissions]
        print("Requesting permissions:", permissionNames)
        nativePermissions = self._myPermissionsToNative(myPermissions)
        self._native_request_permissions(
            [p for p in nativePermissions if not self._native_check_permission(p)]
        )

    def checkPermissions(self, myPermissions: list[PERMISSION_ENUM] = []):
        if not myPermissions:
            myPermissions = self.myPermissions

        if not self.isAndroid:
            print(self._skipping_permissions_message(myPermissions))
            return [True] * len(myPermissions)

        nativePermissions = self._myPermissionsToNative(myPermissions)
        return [self._native_check_permission(p for p in nativePermissions)]
