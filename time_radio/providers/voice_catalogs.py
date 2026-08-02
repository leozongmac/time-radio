from __future__ import annotations

from typing import Literal

from time_radio.models import VoiceCatalogItem, VoiceCatalogResponse

VoiceProvider = Literal["iflytek", "baidu"]

IFLYTEK_VOICES: tuple[VoiceCatalogItem, ...] = (
    VoiceCatalogItem(id="xiaoyan", name="讯飞小燕", category="普通话女声", requires_authorization=True),
    VoiceCatalogItem(id="xiaoyu", name="讯飞小宇", category="普通话男声", requires_authorization=True),
    VoiceCatalogItem(id="xiaofeng", name="讯飞小峰", category="普通话男声", requires_authorization=True),
    VoiceCatalogItem(id="xiaoqi", name="讯飞小琪", category="普通话女声", requires_authorization=True),
    VoiceCatalogItem(id="catherine", name="Catherine", category="英语女声", requires_authorization=True),
    VoiceCatalogItem(id="mary", name="Mary", category="英语女声", requires_authorization=True),
    VoiceCatalogItem(id="x4_xiaoyan", name="讯飞小燕 x4", category="精品普通话女声", requires_authorization=True),
)

BAIDU_VOICES: tuple[VoiceCatalogItem, ...] = (
    VoiceCatalogItem(id="1", name="度小宇", category="基础男声", requires_authorization=False),
    VoiceCatalogItem(id="0", name="度小美", category="基础女声", requires_authorization=False),
    VoiceCatalogItem(id="3", name="度逍遥", category="基础男声", requires_authorization=False),
    VoiceCatalogItem(id="4", name="度丫丫", category="基础女声", requires_authorization=False),
    VoiceCatalogItem(id="5003", name="度逍遥", category="精品男声", requires_authorization=True),
    VoiceCatalogItem(id="5118", name="度小鹿", category="精品女声", requires_authorization=True),
    VoiceCatalogItem(id="106", name="度博文", category="精品男声", requires_authorization=True),
    VoiceCatalogItem(id="110", name="度小童", category="精品童声", requires_authorization=True),
    VoiceCatalogItem(id="111", name="度小萌", category="精品女声", requires_authorization=True),
    VoiceCatalogItem(id="103", name="度米朵", category="精品女声", requires_authorization=True),
    VoiceCatalogItem(id="5", name="度小娇", category="精品女声", requires_authorization=True),
    VoiceCatalogItem(id="4003", name="度逍遥", category="臻品男声", requires_authorization=True),
    VoiceCatalogItem(id="4106", name="度博文", category="臻品男声", requires_authorization=True),
    VoiceCatalogItem(id="4115", name="度小贤", category="臻品男声", requires_authorization=True),
    VoiceCatalogItem(id="4119", name="度小鹿", category="臻品女声", requires_authorization=True),
    VoiceCatalogItem(id="4105", name="度灵儿", category="臻品女声", requires_authorization=True),
    VoiceCatalogItem(id="4117", name="度小乔", category="臻品女声", requires_authorization=True),
    VoiceCatalogItem(id="4100", name="度小雯", category="臻品女声", requires_authorization=True),
    VoiceCatalogItem(id="4103", name="度米朵", category="臻品女声", requires_authorization=True),
    VoiceCatalogItem(id="4144", name="度姗姗", category="臻品女声", requires_authorization=True),
    VoiceCatalogItem(id="4278", name="度小贝", category="臻品女声", requires_authorization=True),
    VoiceCatalogItem(id="4143", name="度清风", category="臻品男声", requires_authorization=True),
    VoiceCatalogItem(id="4140", name="度小新", category="臻品男声", requires_authorization=True),
    VoiceCatalogItem(id="4129", name="度小彦", category="臻品男声", requires_authorization=True),
    VoiceCatalogItem(id="4149", name="度星河", category="臻品男声", requires_authorization=True),
    VoiceCatalogItem(id="4254", name="度小清", category="臻品女声", requires_authorization=True),
    VoiceCatalogItem(id="4206", name="度博文", category="臻品男声", requires_authorization=True),
    VoiceCatalogItem(id="4226", name="南方", category="臻品男声", requires_authorization=True),
    VoiceCatalogItem(id="4189", name="度涵竹", category="大模型女声", requires_authorization=True),
    VoiceCatalogItem(id="4194", name="度嫣然", category="大模型女声", requires_authorization=True),
    VoiceCatalogItem(id="4193", name="度泽言", category="大模型男声", requires_authorization=True),
    VoiceCatalogItem(id="4195", name="度怀安", category="大模型男声", requires_authorization=True),
    VoiceCatalogItem(id="4196", name="度清影", category="大模型女声", requires_authorization=True),
    VoiceCatalogItem(id="4197", name="度沁遥", category="大模型女声", requires_authorization=True),
    VoiceCatalogItem(id="20100", name="度小粤", category="粤语女声", requires_authorization=True),
    VoiceCatalogItem(id="20101", name="度晓芸", category="粤语女声", requires_authorization=True),
    VoiceCatalogItem(id="4257", name="四川小哥", category="四川话男声", requires_authorization=True),
    VoiceCatalogItem(id="4132", name="度阿闽", category="闽南语男声", requires_authorization=True),
    VoiceCatalogItem(id="4139", name="度小蓉", category="四川话女声", requires_authorization=True),
    VoiceCatalogItem(id="5977", name="台媒女声", category="台湾普通话女声", requires_authorization=True),
    VoiceCatalogItem(id="4007", name="度小台", category="台湾普通话女声", requires_authorization=True),
    VoiceCatalogItem(id="4150", name="度湘玉", category="湖南话女声", requires_authorization=True),
    VoiceCatalogItem(id="4134", name="度阿锦", category="东北话女声", requires_authorization=True),
    VoiceCatalogItem(id="4172", name="度筱林", category="方言女声", requires_authorization=True),
)


def get_voice_catalog(provider: VoiceProvider) -> VoiceCatalogResponse:
    if provider == "iflytek":
        return VoiceCatalogResponse(
            provider=provider,
            voices=list(IFLYTEK_VOICES),
            source_note="讯飞 WebAPI 不提供账户发音人枚举接口；请以控制台已授权的 vcn 参数为准。",
        )
    return VoiceCatalogResponse(
        provider=provider,
        voices=list(BAIDU_VOICES),
        source_note="声音目录来自百度短文本在线合成文档；精品、臻品和大模型音色需要对应服务授权。",
    )
