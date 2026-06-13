class GenshinAnalyzerError(Exception):
    """项目内面向用户的基础异常。"""


class CharacterDataError(GenshinAnalyzerError):
    """角色资料同步或读取失败。"""
