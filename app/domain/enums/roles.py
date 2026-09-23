from enum import StrEnum


class UserRole(StrEnum):
    CLIENT = "client"
    MASTER = "master"
    ADMIN = "admin"
