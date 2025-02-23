import datetime
import re
from asyncio import sleep

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg, ArgPlainText
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from LittlePaimon import NICKNAME
from LittlePaimon.database.models import LastQuery, PrivateCookie, PublicCookie, Character, PlayerInfo, DailyNoteSub, MihoyoBBSSub
from LittlePaimon.utils import logger
from LittlePaimon.utils.api import get_bind_game_info, get_stoken_by_cookie
from LittlePaimon.utils.message import recall_message
from LittlePaimon.manager.plugin_manager import plugin_manager as pm

__plugin_meta__ = PluginMetadata(
    name='原神绑定',
    description='原神绑定信息',
    usage='ysb',
    extra={
        'author':   '惜月',
        'version':  '3.0',
        'priority': 2,
    }
)

ysb = on_command('ysb', aliases={'原神绑定', '绑定uid'}, priority=1, block=True, state={
    'pm_name':        'ysb',
    'pm_description': '绑定原神uid或者cookie',
    'pm_usage':       'ysb[uid|cookie]',
    'pm_priority':    1
})
ysbc = on_command('ysbc', aliases={'查询ck', '查询绑定', '绑定信息', '校验绑定'}, priority=1, block=True, state={
    'pm_name':        'ysbc',
    'pm_description': '查询已绑定的原神cookie情况',
    'pm_usage':       'ysbc',
    'pm_priority':    2
})
delete_ck = on_command('删除ck', aliases={'删除cookie'}, priority=1, block=True, state={
    'pm_name':        '删除ck',
    'pm_description': '删除你qq下绑定的cookie和订阅信息',
    'pm_usage':       '删除ck[uid|全部]',
    'pm_priority':    3
})
ysbca = on_command('校验所有ck', aliases={'校验所有cookie', '校验所有绑定'}, priority=1, block=True, permission=SUPERUSER, state={
    'pm_name':        '校验所有ck',
    'pm_description': '校验所有cookie情况，仅超级管理员可用',
    'pm_usage':       '校验所有ck',
    'pm_priority':    4
})
pck = on_command('添加公共cookie', aliases={'添加pck', '添加公共ck', 'add_pck'}, permission=SUPERUSER, block=True, priority=1,
                 state={
                     'pm_name':        '添加公共ck',
                     'pm_description': '添加公共cookie，仅超级管理员可用',
                     'pm_usage':       '添加公共ck[cookie]',
                     'pm_priority':    5
                 })
clear = on_command('清除无效用户', permission=SUPERUSER, block=True, priority=1, state={
    'pm_name':        '清除无效用户',
    'pm_description': '清除所有已退群或已删好友的用户的cookie、订阅等信息，仅超级管理员可用',
    'pm_usage':       '清除无效用户',
    'pm_priority':    6
})


@ysb.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    msg = msg.extract_plain_text().strip()
    if uid := re.search(r'[125]\d{8}', msg):
        await LastQuery.update_or_create(user_id=str(event.user_id),
                                         defaults={'uid': uid.group(), 'last_time': datetime.datetime.now()})
        msg = msg.replace(uid.group(), '').strip()
        if not msg:
            await ysb.finish(f'成功绑定uid为{uid.group()}，如果还需绑定cookie可看教程：\ndocs.qq.com/doc/DQ3JLWk1vQVllZ2Z1',
                             at_sender=True)
    if msg:
        if data := await get_bind_game_info(msg):
            game_name = data['nickname']
            game_uid = data['game_role_id']
            mys_id = data['mys_id']
            await LastQuery.update_or_create(user_id=str(event.user_id),
                                             defaults={'uid': game_uid, 'last_time': datetime.datetime.now()})
            logger.info('原神Cookie', '', {'用户': str(event.user_id), 'uid': game_uid}, '成功绑定cookie', True)
            if 'login_ticket' in msg and (stoken := await get_stoken_by_cookie(msg)):
                await PrivateCookie.update_or_create(user_id=str(event.user_id), uid=game_uid, mys_id=mys_id,
                                                     defaults={'cookie': msg,
                                                               'stoken': f'stuid={mys_id};stoken={stoken};'})
                await ysb.send(f'{game_name}成功绑定cookie{game_uid}，开始愉快地享用{NICKNAME}吧！', at_sender=True)
            else:
                await PrivateCookie.update_or_create(user_id=str(event.user_id), uid=game_uid, mys_id=mys_id,
                                                     defaults={'cookie': msg})
                await ysb.send(f'{game_name}成功绑定cookie{game_uid}，但是cookie中没有login_ticket，米游币相关功能无法使用哦',
                               at_sender=True)
            if not isinstance(event, PrivateMessageEvent):
                if await recall_message(event):
                    await ysb.finish(f'当前非私聊对话，{NICKNAME}帮你把cookie撤回啦！')
                else:
                    await ysb.finish(f'当前非私聊对话，{NICKNAME}建议你绑定完将cookie撤回哦！')
        else:
            logger.info('原神Cookie', '', {'用户': str(event.user_id)}, '绑定失败，cookie已失效', False)
            await ysb.finish('这个cookie无效哦，请确认是否正确\n获取cookie的教程：\ndocs.qq.com/doc/DQ3JLWk1vQVllZ2Z1\n', at_sender=True)
    elif pm.config.CookieWeb_enable:
        await ysb.finish(
            f'获取cookie的教程：\ndocs.qq.com/doc/DQ3JLWk1vQVllZ2Z1\n获取后，使用[ysb cookie]指令绑定或前往{pm.config.CookieWeb_url}网页添加绑定',
            at_sender=True)
    else:
        await ysb.finish('获取cookie的教程：\ndocs.qq.com/doc/DQ3JLWk1vQVllZ2Z1\n获取后，使用[ysb cookie]指令绑定',
                         at_sender=True)


@ysbc.handle()
async def _(event: MessageEvent):
    logger.info('原神Cookie', f'开始校验{str(event.user_id)}的绑定情况')
    ck = await PrivateCookie.filter(user_id=str(event.user_id))
    uid = await LastQuery.get_or_none(user_id=str(event.user_id))
    if ck:
        msg = f'{event.sender.card or event.sender.nickname}当前绑定情况:\n'
        for ck_ in ck:
            if await get_bind_game_info(ck_.cookie):
                msg += f'{ck.index(ck_) + 1}.{ck_.uid}(有效)\n'
            else:
                msg += f'{ck.index(ck_) + 1}.{ck_.uid}(已失效)\n'
                await ck_.delete()
                logger.info('原神Cookie', '➤', {'用户': str(event.user_id), 'uid': ck_.uid}, 'cookie已失效', False)

        await ysbc.finish(msg.strip(), at_sender=True)
    elif uid:
        await ysbc.finish(f'{event.sender.card or event.sender.nickname}当前已绑定uid{uid.uid}，但未绑定cookie', at_sender=True)

    else:
        await ysbc.finish(f'{event.sender.card or event.sender.nickname}当前无绑定信息', at_sender=True)


@delete_ck.handle()
async def _(event: MessageEvent, state: T_State, msg: Message = CommandArg()):
    if uids := await PrivateCookie.filter(user_id=str(event.user_id)):
        state['msg'] = '你已绑定cookie的uid有：\n' + '\n'.join([uid.uid for uid in uids]) + '\n请选择要删除的uid'
        state['uids'] = [uid.uid for uid in uids]
    else:
        await delete_ck.finish('你没有绑定过任何cookie哦', at_sender=True)
    if '全部' in msg.extract_plain_text():
        state['uid'] = Message('全部')
    elif uid := re.search(r'[125]\d{8}', msg.extract_plain_text().strip()):
        state['uid'] = Message(uid.group())


@delete_ck.got('uid', prompt=Message.template('{msg}，或者发送[全部]解绑cookie'))
async def _(event: MessageEvent, state: T_State, uid: str = ArgPlainText('uid')):
    if uid == '全部':
        await PrivateCookie.filter(user_id=str(event.user_id)).delete()
        await DailyNoteSub.filter(user_id=event.user_id).delete()
        await MihoyoBBSSub.filter(user_id=event.user_id).delete()
        await delete_ck.finish('已删除你号下绑定的ck和订阅信息', at_sender=True)
    elif uid in state['uids']:
        await PrivateCookie.filter(user_id=str(event.user_id), uid=uid).delete()
        await DailyNoteSub.filter(user_id=event.user_id, uid=uid).delete()
        await MihoyoBBSSub.filter(user_id=event.user_id, uid=uid).delete()
        await delete_ck.finish(f'已删除UID{uid}绑定的ck和订阅信息', at_sender=True)
    else:
        await delete_ck.finish(state['msg'], at_sender=True)


@ysbca.handle()
async def _(event: MessageEvent):
    logger.info('原神Cookie', '开始校验所有cookie情况')
    await ysbc.send('开始校验全部cookie，请稍等...', at_sender=True)
    private_cookies = await PrivateCookie.all()
    public_cookies = await PublicCookie.all()
    useless_private = []
    useless_public = []
    for cookie in private_cookies:
        if not await get_bind_game_info(cookie.cookie):
            useless_private.append(cookie.uid)
            await cookie.delete()
        await sleep(1)
    for cookie in public_cookies:
        if not await get_bind_game_info(cookie.cookie):
            useless_public.append(str(cookie.id))
            await cookie.delete()
        await sleep(0.5)
    msg = f'当前共{len(public_cookies)}个公共ck，{len(private_cookies)}个私人ck。\n'
    if useless_public:
        msg += '其中失效的公共ck有:' + ' '.join(useless_public) + '\n'
    else:
        msg += '公共ck全部有效\n'
    if useless_private:
        msg += '其中失效的私人ck有:' + ' '.join(useless_private) + '\n'
    else:
        msg += '私人ck全部有效\n'
    await ysbca.finish(msg, at_sender=True)


@pck.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    if msg := msg.extract_plain_text().strip():
        if await get_bind_game_info(msg):
            ck = await PublicCookie.create(cookie=msg)
            logger.info('原神Cookie', f'{ck.id}号公共cookie', None, '添加成功', True)
            await pck.finish(f'成功添加{ck.id}号公共cookie', at_sender=True)
        else:
            logger.info('原神Cookie', '公共cookie', None, '添加失败，cookie已失效', True)
            await pck.finish('这个cookie无效哦，请确认是否正确\n获取cookie的教程：\ndocs.qq.com/doc/DQ3JLWk1vQVllZ2Z1\n', at_sender=True)
    else:
        await pck.finish('获取cookie的教程：\ndocs.qq.com/doc/DQ3JLWk1vQVllZ2Z1\n获取到后，用[添加公共ck cookie]指令添加',
                         at_sender=True)


@clear.handle()
async def _(bot: Bot, event: MessageEvent):
    total_user_list = []
    group_list = await bot.get_group_list()
    for group in group_list:
        group_member_list = await bot.get_group_member_list(group_id=group['group_id'])
        for member in group_member_list:
            if member['user_id'] not in total_user_list:
                total_user_list.append(member['user_id'])
    friend_list = await bot.get_friend_list()
    for friend in friend_list:
        if friend['user_id'] not in total_user_list:
            total_user_list.append(friend['user_id'])
    # 删除私人cookie
    all_private_cookies = await PrivateCookie.all()
    for ck in all_private_cookies:
        if int(ck.user_id) not in total_user_list:
            logger.info('原神Cookie', '私人cookie', {'用户': ck.user_id, 'UID': ck.uid}, '已清除', True)
            await ck.delete()
    # 删除最后查询记录
    all_last_query = await LastQuery.all()
    for q in all_last_query:
        if int(q.user_id) not in total_user_list:
            await q.delete()
    # 删除原神玩家信息
    all_player = await PlayerInfo.all()
    for p in all_player:
        if int(p.user_id) not in total_user_list:
            await p.delete()
    # 删除原神角色
    all_character = await Character.all()
    for chara in all_character:
        if int(chara.user_id) not in total_user_list:
            await chara.delete()
    # # 删除通用订阅信息
    # all_sub = await GeneralSub.all()
    # for s in all_sub:
    #     if int(s.sub_id) not in total_user_list:
    #         await s.delete()
    # 删除原神树脂提醒信息
    all_note = await DailyNoteSub.all()
    for n in all_note:
        if int(n.user_id) not in total_user_list:
            await n.delete()
    # 删除米游社签到及获取信息
    all_sign = await MihoyoBBSSub.all()
    for s in all_sign:
        if int(s.user_id) not in total_user_list:
            await s.delete()

    await clear.finish('清除完成', at_sender=True)
