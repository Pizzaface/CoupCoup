from __future__ import annotations

import asyncio
from json import JSONDecodeError
from typing import Any, Tuple, TypedDict

import loguru
import orjson
from google.generativeai import GenerativeModel as AIStudioGenerativeModel
from google.ai.generativelanguage_v1 import Content as AIStudioContent
from google.generativeai import GenerationConfig as AIStudioGenerationConfig
from google.generativeai.types import Tool as AIStudioTool
from vertexai.generative_models import (
    GenerativeModel,
    GenerationConfig,
    Tool,
    Content,
)
from utils.config import get_config
from utils.jinja import get_template_with_args

MAX_RETRIES = 3

class GeminiCallInput(TypedDict):
    prompt_jinja_template_path: str
    user_input: Any
    logger: loguru.Logger


tool_def = {
    'function_declarations': [
        dict(
            name='extract_rows',
            description='Provides the list of products that were extracted from the messages',
            parameters={
                'type_': 'OBJECT',
                'description': 'Root object that contains the list of products that were extracted from the messages',
                'required': [
                    'products',
                ],
                'properties': {
                    'products': {
                        'description': 'The list of products that were extracted from the messages',
                        'type_': 'ARRAY',
                        'items': {
                            'type_': 'OBJECT',
                            'description': 'A product that was extracted from the messages',
                            'required': [
                                'brand_name',
                                'product_name',
                                'product_variety',
                                'description',
                                'required_purchase_quantity',
                                'price',
                                'sale_percent_off',
                                'sale_amount_off',
                                'sale_price',
                                'quantity_at_sale_price',
                                'quantity_get_free',
                                'quantity_percent_off',
                                'quantity_at_amount_off',
                                'deal_type',
                                'requires_store_card',
                                'valid_from',
                                'valid_to',
                                'required_purchase_amount',
                            ],
                            'properties': {
                                'brand_name': {
                                    'type_': 'STRING',
                                    'nullable': False,
                                    'description': 'The brand name of the product\nExample: `Coca-Cola`, `Kraft`, etc.\n**DO NOT** include multiple brands in this field. **DO NOT DO THIS**: `Coca-Cola | Pepsi`',
                                },
                                'product_name': {
                                    'type_': 'STRING',
                                    'nullable': False,
                                    'description': 'The name of the product - can include modifiers like `organic`, `gluten-free`, etc.',
                                },
                                'product_variety': {
                                    'type_': 'STRING',
                                    'nullable': False,
                                    'description': 'The size/variety of the product - can be a weight, volume, variety, etc.',
                                },
                                'description': {
                                    'type_': 'STRING',
                                    'nullable': True,
                                    'description': 'The description of the sale or coupon',
                                },
                                'required_purchase_quantity': {
                                    'type_': 'NUMBER',
                                    'format': 'int32',
                                    'nullable': False,
                                    'description': 'The minimum NUMBER of items of that product that must be purchased to get the deal - i.e. 2 for $5 would be 2, 1 for $5 would be 1',
                                },
                                'required_purchase_amount': {
                                    'type_': 'NUMBER',
                                    'format': 'int32',
                                    'nullable': False,
                                    'description': 'The minimum amount of money that must be spent to get the deal - i.e. $5 off $20 would be 20',
                                },
                                'price': {
                                    'type_': 'NUMBER',
                                    'format': 'float',
                                    'nullable': False,
                                    'description': "The price of the product, if it is on sale, or a price is given, can include modifiers like 'each' or 'lb'",
                                },
                                'sale_percent_off': {
                                    'type_': 'NUMBER',
                                    'format': 'int32',
                                    'nullable': False,
                                    'description': 'The percent off of the product, if its a PERCENT_OFF deal',
                                },
                                'sale_amount_off': {
                                    'type_': 'NUMBER',
                                    'format': 'float',
                                    'nullable': False,
                                    'description': 'The amount off of the product, if its a AMOUNT_OFF deal',
                                },
                                'sale_price': {
                                    'type_': 'NUMBER',
                                    'format': 'float',
                                    'nullable': False,
                                    'description': 'The sale price of the product, if its a SALE_PRICE deal',
                                },
                                'quantity_at_sale_price': {
                                    'type_': 'NUMBER',
                                    'format': 'int32',
                                    'nullable': False,
                                    'description': 'The amount of products you get at a sale price, if its a BUY_X_GET_Y_AT_Z_AMO_OFF deal',
                                },
                                'quantity_get_free': {
                                    'type_': 'NUMBER',
                                    'format': 'int32',
                                    'nullable': False,
                                    'description': 'The amount of products you get for free, if its a BUY_X_GET_Y_FREE deal - i.e. buy 1 get 1 free, buy 2 get 1 free, etc.',
                                },
                                'quantity_percent_off': {
                                    'type_': 'NUMBER',
                                    'format': 'int32',
                                    'nullable': False,
                                    'description': 'The amount of products you get at a percent off, if its a BUY_X_GET_Y_AT_Z_PER_OFF deal',
                                },
                                'quantity_at_amount_off': {
                                    'type_': 'NUMBER',
                                    'format': 'int32',
                                    'nullable': False,
                                    'description': 'The amount of products you get at an amount off, if its a BUY_X_GET_Y_AT_Z_AMO_OFF deal',
                                },
                                'deal_type': {
                                    'type_': 'STRING',
                                    'nullable': False,
                                    'description': 'The type of deal - extracted from the deal. MUST be one of the following:\n- PERCENT_OFF\n- AMOUNT_OFF\n- BUY_X_GET_Y_AT_Z_PER_OFF\n- BUY_X_GET_Y_AT_Z_AMO_OFF\n- BUY_X_GET_Y_FREE\n- BUY_X_GET_Y_AMOUNT_OFF\n- PRICE_PER_AMOUNT\n- SALE_PRICE\n- OTHER',
                                    'enum': [
                                        'PERCENT_OFF',
                                        'AMOUNT_OFF',
                                        'BUY_X_GET_Y_AT_Z_PER_OFF',
                                        'BUY_X_GET_Y_AT_Z_AMO_OFF',
                                        'BUY_X_GET_Y_FREE',
                                        'BUY_X_GET_Y_AMOUNT_OFF',
                                        'PRICE_PER_AMOUNT',
                                        'SALE_PRICE',
                                        'OTHER',
                                    ],
                                },
                                'requires_store_card': {
                                    'type_': 'BOOLEAN',
                                    'nullable': False,
                                    'description': 'Whether or not the deal requires a store card. This is typically a loyalty card or credit card that is required to get the deal. If the deal does not require a store card, set this to `false`',
                                },
                                'valid_from': {
                                    'type_': 'STRING',
                                    'nullable': True,
                                    'description': 'The date the deal is valid from. Please use the format `YYYY-MM-DD`',
                                },
                                'valid_to': {
                                    'type_': 'STRING',
                                    'nullable': False,
                                    'description': 'The date the deal is valid to. Please use the format `YYYY-MM-DD`',
                                },
                            },
                        },
                    },
                },
            },
        )
    ]
}


async def make_aistudio_gemini_call(
    history: list[AIStudioContent],
    logger,
    model_name: str = 'gemini-1.0-pro-001',
    **model_options,
):
    # Initialize Gemini model
    model = AIStudioGenerativeModel(model_name, tools=tool_def)

    retry = 0
    content = None
    while retry < MAX_RETRIES:
        try:
            content = await model.generate_content_async(
                contents=history,
                tools=[AIStudioTool(**tool_def)],
                generation_config=AIStudioGenerationConfig(**model_options),
                safety_settings={
                    'HARASSMENT': 'block_none',
                    'HATE_SPEECH': 'block_none',
                    'DANGEROUS': 'block_none',
                    'SEXUAL': 'block_none',
                },
            )
        except Exception as e:
            if '429' in str(e):
                logger.warning(
                    f'Gemini returned a 429 error. Waiting 60 seconds before retrying.'
                )
                await asyncio.sleep(60)

            elif retry == MAX_RETRIES - 1:
                logger.warning(
                    f'Gemini returned an invalid response on last retry. Error: {e}'
                )
                raise e
            else:
                logger.warning(
                    f'Gemini returned an invalid response (retry {retry}). Error: {e}'
                )
                await asyncio.sleep(3)

            retry += 1
            continue

        break

    return content


async def make_vertex_gemini_call(
    history: list[Content],
    logger,
    model_name: str = 'gemini-1.0-pro-001',
    **model_options,
):
    # Initialize Gemini model
    model = GenerativeModel(model_name)

    retry = 0
    content = None
    while retry < MAX_RETRIES:
        try:
            content = await model.generate_content_async(
                contents=history,
                generation_config=GenerationConfig(**model_options),
                tools=[Tool.from_dict(tool_def)],
            )
        except Exception as e:
            if '429' in str(e):
                logger.warning(
                    f'Gemini returned a 429 error. Waiting 60 seconds before retrying.'
                )
                await asyncio.sleep(60)

            elif retry == MAX_RETRIES - 1:
                logger.warning(
                    f'Gemini returned an invalid response on last retry. Error: {e}'
                )
                raise e
            else:
                logger.warning(
                    f'Gemini returned an invalid response (retry {retry}). Error: {e}'
                )
                await asyncio.sleep(3)

            retry += 1
            continue

        break

    return content


async def extract_products_using_gemini(
    args: GeminiCallInput,
    **template_arguments,
) -> Tuple[list[dict[str, str]], Any] | None:
    prompt_jinja_template_path = args['prompt_jinja_template_path']
    user_input = args['user_input']
    logger = args['logger']

    config = get_config()
    default_section = config['config']

    (
        model_name,
        model_temp,
        model_top_k,
        model_top_p,
        prompt_str,
        prompt_input,
    ) = await setup_gemini_prompt(
        default_section=default_section,
        template_arguments=template_arguments,
        prompt_jinja_template_path=prompt_jinja_template_path,
        user_input_text=user_input,
    )

    gemini_response = None
    if 'GOOGLE_API_KEY' in default_section:
        gemini_response = await handle_ai_studio_generate(
            logger=logger,
            model_name=model_name,
            model_temp=model_temp,
            model_top_k=model_top_k,
            model_top_p=model_top_p,
            prompt_str=prompt_str,
            user_input_text=prompt_input,
        )

    elif 'GOOGLE_PROJECT_ID' in default_section:
        gemini_response = await handle_vertex_ai_generate(
            logger=logger,
            model_name=model_name,
            model_temp=model_temp,
            model_top_k=model_top_k,
            model_top_p=model_top_p,
            prompt_str=prompt_str,
            user_input_text=prompt_input,
        )

    try:
        if gemini_response is None:
            return [], user_input

        items = handle_gemini_response(gemini_response)
    except Exception as e:
        logger.error(e)
        return [], user_input

    return items, user_input


def handle_gemini_response(gemini_response):
    if (
        gemini_response is None
        or not gemini_response.candidates
        or not hasattr(gemini_response.candidates[0], 'content')
        or not hasattr(gemini_response.candidates[0].content, 'parts')
        or not hasattr(
            gemini_response.candidates[0].content.parts[0], 'function_call'
        )
    ):
        raise KeyError('Invalid response from Gemini')

    function_call = (
        gemini_response.candidates[0].content.parts[0].function_call
    )

    arguments = function_call.args

    if arguments is None or 'products' not in arguments:
        return []

    try:
        items = [dict(x) for x in arguments['products']]
    except Exception as e:
        raise e

    return items


async def handle_vertex_ai_generate(
    logger,
    model_name,
    model_temp,
    model_top_k,
    model_top_p,
    prompt_str,
    user_input_text,
):
    history = [
        Content.from_dict(
            {
                'role': 'user',
                'parts': [{'text': f'{prompt_str}\n{user_input_text}'}],
            }
        )
    ]

    try:
        gemini_response = await make_vertex_gemini_call(
            history,
            model_name=model_name,
            logger=logger,
            temperature=model_temp,
            top_k=model_top_k,
            top_p=model_top_p,
        )
    except Exception as e:
        logger.error(e)
        return None

    return gemini_response


async def handle_ai_studio_generate(
    logger,
    model_name,
    model_temp,
    model_top_k,
    model_top_p,
    prompt_str,
    user_input_text,
):
    history = [
        dict(
            role='user',
            parts=[{'text': f'{prompt_str}\n{user_input_text}'}],
        )
    ]

    try:
        # noinspection PyTypeChecker
        gemini_response = await make_aistudio_gemini_call(
            history,
            model_name=model_name,
            logger=logger,
            temperature=model_temp,
            top_k=model_top_k,
            top_p=model_top_p,
        )
    except Exception as e:
        logger.error(e)
        return None

    return gemini_response


async def setup_gemini_prompt(
    default_section,
    template_arguments,
    prompt_jinja_template_path,
    user_input_text,
):
    if (
        'GOOGLE_API_KEY' not in default_section
        and 'GOOGLE_PROJECT_ID' not in default_section
    ):
        raise Exception('No Google API key or project ID found in config.ini')

    user_input_text = (
        str(user_input_text)
        if not isinstance(user_input_text, str)
        else f'```json\n{orjson.dumps(user_input_text, option=orjson.OPT_INDENT_2 + orjson.OPT_SORT_KEYS).decode("latin-1")}```'
    )

    prompt_str = await get_template_with_args(
        prompt_jinja_template_path, **template_arguments
    )

    model_name = default_section.get('MODEL_NAME', 'gemini-1.0-pro-001')
    model_temp = float(default_section.get('MODEL_TEMP', 1.0))
    model_top_k = int(default_section.get('MODEL_TOP_K', 0)) or None
    model_top_p = min(float(default_section.get('MODEL_TOP_P', 0)), 2) or None

    return (
        model_name,
        model_temp,
        model_top_k,
        model_top_p,
        prompt_str,
        user_input_text,
    )
