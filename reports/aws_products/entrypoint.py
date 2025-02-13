from cnct import R
from reports.utils import (
    convert_to_datetime,
    get_asset_parameter,
    get_value,
)

awsmpn = {}


def get_aws_mpn(client, account, product):
    if awsmpn.get(account):
        return awsmpn.get(account)
    rql_filter = R()
    rql_filter &= R().product.id.eq(product)
    rql_filter &= R().account.id.eq(account)
    tc = client.ns('tier').configs.filter(rql_filter).first()
    if tc:
        for param in tc['params']:
            if param['id'] == 'awsApnId':
                awsmpn['account'] = param.get('value', '-')
                return param.get('value', '-')
    return '-'


def warm_up_tcs(client, products):
    rql_filter = R()
    rql_filter &= R().product.id.oneof(products)
    tcs = client.ns('tier').configs.filter(rql_filter).all()
    for tc in tcs:
        if not awsmpn.get(f'{tc["account"]["id"]}_{tc["product"]["id"]}'):
            for param in tc['params']:
                if param['id'] == 'awsApnId':
                    awsmpn[f'{tc["account"]["id"]}_{tc["product"]["id"]}'] = param.get('value', '-')


def get_awsmpn(account, product):
    return awsmpn.get(f'{account}_{product}', '-')


def generate(client, parameters, progress_callback):
    warm_up_tcs(client, parameters['products']['choices'])
    subscriptions_rql = R()
    if not parameters.get("products") or len(parameters['products']['choices']) < 1:
        raise RuntimeError("AWS products was not selected")
    if parameters.get("date"):
        subscriptions_rql &= R().events.created.at.ge(parameters['date']['after'])
        subscriptions_rql &= R().events.created.at.le(parameters['date']['before'])
    subscriptions_rql &= R().product.id.oneof(parameters['products']['choices'])
    subscriptions_rql &= R().status.ne('draft')
    subscriptions = client.assets.filter(subscriptions_rql)
    total_subscriptions = subscriptions.count()
    progress = 0
    for subscription in subscriptions:
        yield (
            subscription['id'],
            subscription.get('external_id', "-"),
            subscription['status'],
            subscription['marketplace']['name'],
            subscription['product']['id'],
            convert_to_datetime(subscription['events']['created']['at']),
            get_asset_parameter(subscription, "awsAccountId"),
            get_value(subscription['tiers'], "customer", "external_id"),
            get_value(subscription['tiers'], "customer", "name"),
            get_value(subscription['tiers']["customer"], "contact_info", "address_line1"),
            get_value(subscription['tiers']["customer"], "contact_info", "address_line2"),
            get_value(subscription['tiers']["customer"], "contact_info", "city"),
            get_value(subscription['tiers']["customer"], "contact_info", "state"),
            get_value(subscription['tiers']["customer"], "contact_info", "postal_code"),
            get_value(subscription['tiers']["customer"], "contact_info", "country"),
            get_value(subscription['tiers']["customer"]["contact_info"], "contact", "email"),
            get_asset_parameter(subscription, "isGovernmentEntity"),
            get_asset_parameter(subscription, "useAccountFor"),
            get_asset_parameter(subscription, "orderMode"),
            get_value(subscription['tiers'], "tier1", "external_id"),
            get_value(subscription['tiers'], "tier1", "name"),
            get_value(subscription['tiers']["tier1"], "contact_info", "address_line1"),
            get_value(subscription['tiers']["tier1"], "contact_info", "address_line2"),
            get_value(subscription['tiers']["tier1"], "contact_info", "city"),
            get_value(subscription['tiers']["tier1"], "contact_info", "state"),
            get_value(subscription['tiers']["tier1"], "contact_info", "postal_code"),
            get_value(subscription['tiers']["tier1"], "contact_info", "country"),
            get_value(subscription['tiers']["tier1"]["contact_info"], "contact", "email"),
            # get_aws_mpn(client, get_value(subscription['tiers'], "tier1", 'id'), subscription['product']['id'])
            get_awsmpn(get_value(subscription['tiers'], "tier1", 'id'), subscription['product']['id'])
        )
        progress += 1
        progress_callback(progress, total_subscriptions)
