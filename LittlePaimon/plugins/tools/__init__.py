from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.plugin import PluginMetadata
from LittlePaimon import SUPERUSERS
from LittlePaimon.manager.plugin_manager import plugin_manager as pm
from LittlePaimon.utils.brower import AsyncPlaywright


async def permission_check(event: MessageEvent) -> bool:
    if pm.config.screenshot_enable:
        return True
    return event.user_id not in SUPERUSERS and event.sender.role not in ['admin', 'owner']


__plugin_meta__ = PluginMetadata(
    name='实用工具',
    description='一些实用的工具插件',
    usage='',
    extra={
        'author':   '惜月',
        'version':  '3.0',
        'priority': 99,
    }
)

screenshot_cmd = on_command('网页截图', priority=10, block=True, rule=Rule(permission_check), state={
    'pm_name':        '网页截图',
    'pm_description': '对指定链接页面进行截图，例：【网页截图www.baidu.com】',
    'pm_usage':       '网页截图<链接>',
    'pm_priority':    1
})


@screenshot_cmd.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    await screenshot_cmd.send('正在尝试截图，请稍等...')
    url = msg.extract_plain_text().strip()
    img = await AsyncPlaywright.screenshot(url)
    await screenshot_cmd.send(img)


