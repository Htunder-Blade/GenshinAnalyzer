class GenshinAnalyserError(Exception):
    """项目内面向用户的基础异常。"""


class CharacterDataError(GenshinAnalyserError):
    """角色资料同步或读取失败。"""
