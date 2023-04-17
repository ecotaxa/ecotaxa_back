# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Mypy plugin for models combining primitives
#
from typing import Optional, Callable, Tuple, Dict

from mypy.nodes import (
    SymbolTableNode,
    ClassDef,
    Block,
    TypeInfo,
    SymbolTable,
    GDEF,
    NameExpr,
    Var,
    FuncDef,
    TypeVarExpr,
    Decorator,
)
from mypy.plugin import (
    Plugin,
    DynamicClassDefContext,
)
from mypy.types import Instance, Type

ColTypesT = Dict[str, Type]


def _get_2_call_args(ctx: DynamicClassDefContext) -> Tuple[TypeInfo, TypeInfo]:
    arg1, arg2 = ctx.call.args
    if not isinstance(arg1, NameExpr) or not isinstance(arg2, NameExpr):
        ctx.api.msg.fail(
            "EcoTaxa plugin: Class args "
            + str(arg1)
            + " and "
            + str(arg2)
            + " must be simple names",
            None,
        )
    assert isinstance(arg1, NameExpr) and isinstance(arg2, NameExpr)
    return _get_class_info_from_arg(ctx, arg1), _get_class_info_from_arg(ctx, arg2)


def _db_model_2_pydantic_class_maker_callback(ctx: DynamicClassDefContext) -> None:
    db_model_type_info, pydantic_model_type_info = _get_2_call_args(ctx)

    col_types: ColTypesT = {}
    for a_col, a_type in db_model_type_info.names.items():
        if "Mapped" in str(a_type.type):
            # e.g. sqlalchemy.orm.attributes.Mapped[Union[builtins.int, None]]
            col_types[a_col] = a_type.type.args[0]  # type:ignore

    class_name = ctx.name
    _add_pydantic_clone(
        ctx, class_name, pydantic_model_type_info, col_types, from_orm=True
    )


def _dataclass_2_pydantic_class_maker_callback_with_suffix(
    ctx: DynamicClassDefContext,
) -> None:
    return _dataclass_2_pydantic_class_maker_callback(ctx, True)


def _dataclass_2_pydantic_class_maker_callback_without_suffix(
    ctx: DynamicClassDefContext,
) -> None:
    return _dataclass_2_pydantic_class_maker_callback(ctx, False)


def _dataclass_2_pydantic_class_maker_callback(
    ctx: DynamicClassDefContext, with_suffix: bool = False
) -> None:
    data_class_type_info, pydantic_model_type_info = _get_2_call_args(ctx)

    col_types: ColTypesT = {}
    for a_col, a_type in data_class_type_info.names.items():
        try:
            col_types[a_col] = a_type.type  # type:ignore
        except ValueError:
            pass

    class_name = data_class_type_info.name + ("Model" if with_suffix else "")
    _add_pydantic_clone(ctx, class_name, pydantic_model_type_info, col_types)


def _typeddict_2_pydantic_class_maker(ctx: DynamicClassDefContext) -> None:
    typeddict_type_info, pydantic_model_type_info = _get_2_call_args(ctx)

    typeddict_type = typeddict_type_info.typeddict_type
    if typeddict_type is None:
        ctx.api.msg.fail(
            "EcoTaxa plugin: TypedDict arg "
            + str(typeddict_type_info)
            + " is not a typed dict",
            None,
        )
    assert typeddict_type
    col_types: ColTypesT = {}
    for a_field_name, an_info in typeddict_type.items.items():
        col_types[a_field_name] = an_info

    class_name = typeddict_type_info.name.replace("Dict", "Model")
    _add_pydantic_clone(ctx, class_name, pydantic_model_type_info, col_types)


def _get_class_info_from_arg(
    ctx: DynamicClassDefContext, class_arg: NameExpr
) -> TypeInfo:
    class_name = class_arg.fullname
    if class_name is None:
        ctx.api.msg.fail(
            "EcoTaxa plugin: Class arg " + str(class_arg) + " has no name", None
        )
    assert class_name
    return _get_class_info(ctx, class_name)


def _get_class_info(ctx: DynamicClassDefContext, class_name: str) -> TypeInfo:
    class_info = ctx.api.lookup_fully_qualified_or_none(class_name)
    if class_info is None:
        ctx.api.msg.fail("EcoTaxa plugin: Cannot find class:" + class_name, None)
    assert class_info
    class_type_info: Optional[TypeInfo] = class_info.node  # type:ignore
    if class_type_info is None:
        ctx.api.msg.fail("EcoTaxa plugin: Class '" + class_name + "' has no node", None)
    assert class_type_info
    return class_type_info


def _add_pydantic_clone(
    ctx: DynamicClassDefContext,
    class_name: str,
    pydantic_model_type_info: TypeInfo,
    col_types: ColTypesT,
    from_orm: bool = False,
):
    # Fetch from context the base & metaclasses
    base_model_info = _get_class_info(ctx, "pydantic.main.BaseModel")
    metaclass_info = _get_class_info(ctx, "pydantic.main.ModelMetaclass")
    # Build the class to register
    cls = ClassDef(ctx.name, Block([]))
    cls.fullname = ctx.api.qualified_name(class_name)
    info = TypeInfo(SymbolTable(), cls, ctx.api.cur_mod_id)
    cls.info = info
    info.metaclass_type = Instance(metaclass_info, [])
    info.bases = [Instance(base_model_info, [])]
    info.mro = [info] + base_model_info.mro
    info.fallback_to_any = False  # Strict check of fields
    info.metadata = pydantic_model_type_info.metadata.copy()
    if from_orm:
        info.metadata["pydantic-mypy-metadata"]["config"]["orm_mode"] = True
    # Clone names
    info_names = SymbolTable()
    for a_name, a_sym in pydantic_model_type_info.names.items():
        sym_copy = a_sym.copy()
        sym_node = sym_copy.node
        # detach from copied class
        if isinstance(sym_node, Var):  # e.g. depthmax
            sym_node.info = info
            if a_name not in col_types:
                ctx.api.msg.fail(
                    "EcoTaxa plugin: No type info for field '"
                    + a_name
                    + "' while augmenting "
                    + str(pydantic_model_type_info.fullname),
                    None,
                )
            else:
                sym_node.type = col_types[a_name]
        elif isinstance(sym_node, FuncDef):  # e.g.  __init__
            continue
        elif isinstance(sym_node, TypeInfo):  # e.g. Config
            continue
        elif isinstance(sym_node, TypeVarExpr):  # e.g. _PydanticBaseModel
            continue
        elif isinstance(sym_node, Decorator):  # e.g. construct
            continue
        else:
            ctx.api.msg.fail("EcoTaxa plugin: Cannot clone:" + str(sym_copy), None)
        info_names[a_name] = sym_copy
    info.names = info_names
    # For debugging: info.dump()
    # Store in context
    ctx.api.add_symbol_table_node(ctx.name, SymbolTableNode(GDEF, info))


class CustomPlugin(Plugin):
    # The magic primitive DB model + Pydantic model -> Pydantic model
    DB_2_PYDANTIC = "API_models.helpers.DBtoModel.combine_models"
    # The magic primitives Dataclass + Pydantic model -> Pydantic model
    DATACLASS_2_PYDANTIC = "API_models.helpers.DataclassToModel.dataclass_to_model"
    DATACLASS_2_PYDANTIC_WITH_SUFFIX = (
        "API_models.helpers.DataclassToModel.dataclass_to_model_with_suffix"
    )
    # The magic primitive TypedDict + Pydantic model -> Pydantic model
    TYPEDDICT_2_PYDANTIC = "API_models.helpers.TypedDictToModel.typed_dict_to_model"

    def get_dynamic_class_hook(
        self, fullname: str
    ) -> Optional[Callable[[DynamicClassDefContext], None]]:
        if fullname == self.DB_2_PYDANTIC:
            return _db_model_2_pydantic_class_maker_callback
        elif fullname == self.DATACLASS_2_PYDANTIC:
            return _dataclass_2_pydantic_class_maker_callback_without_suffix
        elif fullname == self.DATACLASS_2_PYDANTIC_WITH_SUFFIX:
            return _dataclass_2_pydantic_class_maker_callback_with_suffix
        elif fullname == self.TYPEDDICT_2_PYDANTIC:
            return _typeddict_2_pydantic_class_maker
        return None


def plugin(version: str):
    # ignore version argument if the plugin works with all mypy versions.
    return CustomPlugin
