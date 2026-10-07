from LLM_SYS import BioBrainAgent
from IO_SYS import GraphVisualizer,PDFProcessor
import os
import re
import collections
import concurrent.futures

# =====================================================================
# 0. 拓扑关系规整与提纯引擎（无向折叠、同种合并与机制提纯）
# =====================================================================
def is_symmetric_relation(rel_type: str) -> bool:
    """
    判断关系是否属于无向/对称关系（如'相关'、'相互作用'、'结合'等）。
    对于对称关系，A->B 与 B->A 在语义与图拓扑上完全等价，应折叠为单一规范方向连线。
    """
    if not rel_type or not isinstance(rel_type, str):
        return True  # 默认缺省视为粗糙相关

    r = rel_type.strip().lower()

    # 1. 强有向关系关键词（绝不对称）
    directed_markers = [
        "正作用", "负作用", "包含", "激活", "促进", "抑制", "阻断", "拮抗",
        "上调", "下调", "降解", "磷酸化", "转录", "诱导", "表达",
        "activate", "inhibit", "suppress", "promote", "contain", "include",
        "upregulate", "downregulate", "phosphorylat", "induce"
    ]
    for dm in directed_markers:
        if dm in r:
            return False

    # 2. 经典对称/互作/无向关系关键词
    symmetric_markers = [
        "相关", "关联", "相互作用", "结合", "复合物", "互作",
        "interact", "correlat", "associat", "bind", "complex"
    ]
    for sm in symmetric_markers:
        if sm in r:
            return True

    # 3. 兜底判断：系统标准分类中除明确有向动作外，其余均作为粗糙对称连线处理
    return True


def is_mechanism_relation(rel_type: str) -> bool:
    """判断是否为明确的具体因果机制或层级关系（如'正作用'、'负作用'、'包含'等）"""
    return not is_symmetric_relation(rel_type)


def merge_relation_attributes(target_item: dict, incoming_item: dict) -> dict:
    """
    通用关系属性无损聚合合并：
    将 incoming_item 的权重热度 (weight)、原文证据 (evidence)、文献来源 (doc_source)、
    文献哈希 (doc_hash) 与原因说明 (reason) 无损合并入 target_item。
    """
    if not isinstance(target_item, dict) or not isinstance(incoming_item, dict):
        return target_item

    # 1. 权重热度累加
    w_tgt = target_item.get("weight", 1)
    w_inc = incoming_item.get("weight", 1)
    try:
        w_tgt = float(w_tgt) if "." in str(w_tgt) else int(w_tgt)
    except Exception:
        w_tgt = 1
    try:
        w_inc = float(w_inc) if "." in str(w_inc) else int(w_inc)
    except Exception:
        w_inc = 1
    target_item["weight"] = w_tgt + w_inc

    # 2. 证据原文无损拼接与去重
    old_ev = str(target_item.get("evidence", "")).strip()
    new_ev = str(incoming_item.get("evidence", "")).strip()
    if new_ev and new_ev != "无":
        if not old_ev or old_ev == "无":
            target_item["evidence"] = new_ev
        elif new_ev not in old_ev:
            target_item["evidence"] = f"{old_ev}\n---\n{new_ev}"

    # 3. 文献来源去重合并 (以 ' | ' 分隔)
    old_doc = str(target_item.get("doc_source", "")).strip()
    new_doc = str(incoming_item.get("doc_source", "")).strip()
    if new_doc and new_doc != "未知文献":
        if not old_doc or old_doc == "未知文献":
            target_item["doc_source"] = new_doc
        else:
            docs_exist = [d.strip() for d in old_doc.split("|") if d.strip()]
            docs_new = [d.strip() for d in new_doc.split("|") if d.strip()]
            for d in docs_new:
                if d not in docs_exist:
                    docs_exist.append(d)
            target_item["doc_source"] = " | ".join(docs_exist)

    # 4. 文献哈希去重合并
    old_hash = str(target_item.get("doc_hash", "")).strip()
    new_hash = str(incoming_item.get("doc_hash", "")).strip()
    if new_hash:
        if not old_hash:
            target_item["doc_hash"] = new_hash
        else:
            hashes_exist = [h.strip() for h in old_hash.split("|") if h.strip()]
            hashes_new = [h.strip() for h in new_hash.split("|") if h.strip()]
            for h in hashes_new:
                if h not in hashes_exist:
                    hashes_exist.append(h)
            target_item["doc_hash"] = " | ".join(hashes_exist)

    # 5. 原因说明去重合并
    old_reason = str(target_item.get("reason", "")).strip()
    new_reason = str(incoming_item.get("reason", "")).strip()
    if new_reason:
        if not old_reason:
            target_item["reason"] = new_reason
        elif new_reason not in old_reason:
            target_item["reason"] = f"{old_reason} | {new_reason}"

    # 6. 捷径标记（任一为捷径则保留为捷径）
    if incoming_item.get("is_shortcut") is True or str(incoming_item.get("is_shortcut")).lower() == "true":
        target_item["is_shortcut"] = True

    return target_item


def consolidate_homogeneous_relations(relations: list) -> list:
    """
    同种关系合并（去重、对称折叠与属性聚合）：
    1. 针对对称关系（如“相关”）：将双向 A->B 与 B->A 规整为统一标准方向（按字典序规范节点对，如 min(A,B) -> max(A,B)）；
    2. 针对有向关系（如“正作用”、“负作用”、“包含”）：保持方向独立性，仅合并同向同类型的重复边；
    3. 合并属性：累加热度权重 (weight)，按段落去重无损拼接原文证据 (evidence)，
       去重拼接文献出处 (doc_source) 与文献哈希 (doc_hash)，合并分析原因 (reason)。
    """
    if not relations:
        return []

    master_map = {}
    ordered_keys = []

    for rel in relations:
        if not isinstance(rel, dict):
            continue

        s = str(rel.get("source", "")).strip()
        t = str(rel.get("target", "")).strip()
        r = str(rel.get("relation", "")).strip()

        if not s or not t:
            continue

        # 确定规范方向与聚合主键
        if is_symmetric_relation(r):
            # 对称关系：按字典序规范方向，A->B 与 B->A 映射为同一主键
            if s <= t:
                canon_s, canon_t = s, t
            else:
                canon_s, canon_t = t, s
            key = (canon_s, canon_t, r)
        else:
            # 有向关系：严格保持方向
            canon_s, canon_t = s, t
            key = (s, t, r)

        if key in master_map:
            existing = master_map[key]
            merge_relation_attributes(existing, rel)
        else:
            # 全新边：复制字典并规范化端点
            new_entry = dict(rel)
            new_entry["source"] = canon_s
            new_entry["target"] = canon_t
            new_entry["relation"] = r
            if "weight" not in new_entry:
                new_entry["weight"] = 1
            master_map[key] = new_entry
            ordered_keys.append(key)

    return [master_map[k] for k in ordered_keys]


def purify_mechanism_relations(relations: list) -> list:
    """
    不同关系提纯（高阶机制吸收覆盖粗糙相关连线）：
    当同一对实体（无视方向）之间同时存在高信息量的具体机制/层级关系（如'正作用'、'负作用'、'包含'）
    与低信息量的笼统'相关'关系时：
    1. 将粗糙'相关'关系的原文证据、文献出处、哈希与权重热度完整无损地合并转移至该机制连线上；
    2. 从图谱中彻底剔除已被机制覆盖的粗糙'相关'冗余连线；
    3. 若两节点间仅有机制关系，或仅有粗糙相关关系，则予以完整保留。
    """
    if not relations:
        return []

    # 1. 按无向实体对归组
    pair_groups = {}
    for rel in relations:
        if not isinstance(rel, dict):
            continue
        s = str(rel.get("source", "")).strip()
        t = str(rel.get("target", "")).strip()
        if not s or not t:
            continue
        pair = (min(s, t), max(s, t))
        if pair not in pair_groups:
            pair_groups[pair] = []
        pair_groups[pair].append(rel)

    purified_relations = []

    for pair, rel_list in pair_groups.items():
        # 分离明确机制关系与粗糙相关关系
        mechanisms = [r for r in rel_list if is_mechanism_relation(r.get("relation", ""))]
        coarse_rels = [r for r in rel_list if not is_mechanism_relation(r.get("relation", ""))]

        if mechanisms and coarse_rels:
            # 存在机制连线覆盖粗糙相关线：将 coarse_rels 的证据/权重/出处无损吸收进机制关系
            for c_rel in coarse_rels:
                c_src = str(c_rel.get("source", "")).strip()
                c_tgt = str(c_rel.get("target", "")).strip()

                # 优先匹配同向机制关系，若无则吸收进首个机制关系
                matched_mech = next(
                    (m for m in mechanisms if str(m.get("source", "")).strip() == c_src and str(m.get("target", "")).strip() == c_tgt),
                    mechanisms[0]
                )

                # 1. 权重热度转移
                w_mech = matched_mech.get("weight", 1)
                w_coarse = c_rel.get("weight", 1)
                try:
                    w_mech = float(w_mech) if "." in str(w_mech) else int(w_mech)
                    w_coarse = float(w_coarse) if "." in str(w_coarse) else int(w_coarse)
                    matched_mech["weight"] = w_mech + w_coarse
                except Exception:
                    pass

                # 2. 证据原文无损拼接与去重
                old_ev = str(matched_mech.get("evidence", "")).strip()
                new_ev = str(c_rel.get("evidence", "")).strip()
                if new_ev and new_ev != "无":
                    if not old_ev or old_ev == "无":
                        matched_mech["evidence"] = new_ev
                    elif new_ev not in old_ev:
                        matched_mech["evidence"] = f"{old_ev}\n---\n{new_ev}"

                # 3. 文献来源去重合并
                old_doc = str(matched_mech.get("doc_source", "")).strip()
                new_doc = str(c_rel.get("doc_source", "")).strip()
                if new_doc and new_doc != "未知文献":
                    if not old_doc or old_doc == "未知文献":
                        matched_mech["doc_source"] = new_doc
                    else:
                        docs_exist = [d.strip() for d in old_doc.split("|") if d.strip()]
                        docs_new = [d.strip() for d in new_doc.split("|") if d.strip()]
                        for d in docs_new:
                            if d not in docs_exist:
                                docs_exist.append(d)
                        matched_mech["doc_source"] = " | ".join(docs_exist)

                # 4. 文献哈希去重合并
                old_hash = str(matched_mech.get("doc_hash", "")).strip()
                new_hash = str(c_rel.get("doc_hash", "")).strip()
                if new_hash:
                    if not old_hash:
                        matched_mech["doc_hash"] = new_hash
                    else:
                        hashes_exist = [h.strip() for h in old_hash.split("|") if h.strip()]
                        hashes_new = [h.strip() for h in new_hash.split("|") if h.strip()]
                        for h in hashes_new:
                            if h not in hashes_exist:
                                hashes_exist.append(h)
                        matched_mech["doc_hash"] = " | ".join(hashes_exist)

                # 5. 原因说明去重合并
                old_reason = str(matched_mech.get("reason", "")).strip()
                new_reason = str(c_rel.get("reason", "")).strip()
                if new_reason:
                    if not old_reason:
                        matched_mech["reason"] = new_reason
                    elif new_reason not in old_reason:
                        matched_mech["reason"] = f"{old_reason} | {new_reason}"

            # 仅保留吸收了粗糙证据的机制关系，粗糙相关关系被剔除
            purified_relations.extend(mechanisms)
        else:
            # 只有机制关系或只有粗糙关系，全部保留
            purified_relations.extend(rel_list)

    return purified_relations


def merge_coarse_relation_into_target(relations: list, src: str, tgt: str, coarse_rel: str = "相关", target_rel: str = None) -> list:
    """
    单对节点间粗糙关系的提纯合并：
    将指定实体对间的粗糙关系（如'相关'）的证据、文献来源、哈希和权重热度，
    无损合并入同对实体间的具体机制关系（如'正作用'、'负作用'、'包含'）中，并安全移除该粗糙关系。
    若找不到对应机制关系，则回退为安全保留或按需剔除。
    """
    if not relations:
        return []

    s_clean = str(src).strip()
    t_clean = str(tgt).strip()
    r_clean = str(coarse_rel).strip()

    # 1. 查找待合并的粗糙关系条目
    coarse_idx = -1
    for i, rel in enumerate(relations):
        rs = str(rel.get("source", "")).strip()
        rt = str(rel.get("target", "")).strip()
        rr = str(rel.get("relation", "")).strip()
        if ((rs == s_clean and rt == t_clean) or (rs == t_clean and rt == s_clean)) and rr == r_clean:
            coarse_idx = i
            break

    if coarse_idx == -1:
        return relations

    coarse_item = relations[coarse_idx]

    # 2. 查找接收证据的目标机制关系
    target_item = None
    for rel in relations:
        if rel is coarse_item:
            continue
        rs = str(rel.get("source", "")).strip()
        rt = str(rel.get("target", "")).strip()
        rr = str(rel.get("relation", "")).strip()
        if (rs == s_clean and rt == t_clean) or (rs == t_clean and rt == s_clean):
            if target_rel:
                if rr == str(target_rel).strip():
                    target_item = rel
                    break
            else:
                if is_mechanism_relation(rr):
                    target_item = rel
                    break

    # 3. 若找到目标机制，执行无损属性吸收
    if target_item is not None:
        merge_relation_attributes(target_item, coarse_item)
        # 4. 只有在成功吸收合并入目标机制后，才剔除粗糙关系！
        relations.pop(coarse_idx)
    else:
        # 🛡️ 安全防漏保护：若未找到目标机制关系，坚决不 pop，原样安全保留该粗糙关系！
        print(f"   ⚠️ [提纯防漏] 未在 '{s_clean}' 与 '{t_clean}' 之间找到可吸收的目标机制关系，安全保留粗糙连线。")

    return relations


def fold_symmetric_relations(relations: list, node_a: str, node_b: str, relation: str = "相关") -> list:
    """
    单对节点间双向对称连线的折叠合并：
    将 node_a 与 node_b 之间的同种对称关系（如'相关'）合并为单向规范条目，
    无损累加热度权重，无损拼接去重证据原文与文献出处，抹除反向冗余连线。
    """
    if not relations:
        return []

    a_clean = str(node_a).strip()
    b_clean = str(node_b).strip()
    r_clean = str(relation).strip()

    # 规范化方向（按字典序确定规范条目的 source 与 target）
    if a_clean <= b_clean:
        canon_s, canon_t = a_clean, b_clean
    else:
        canon_s, canon_t = b_clean, a_clean

    canonical_item = None
    to_absorb = []
    remaining = []

    for rel in relations:
        if not isinstance(rel, dict):
            continue
        s = str(rel.get("source", "")).strip()
        t = str(rel.get("target", "")).strip()
        r = str(rel.get("relation", "")).strip()

        is_pair = ((s == a_clean and t == b_clean) or (s == b_clean and t == a_clean))
        if is_pair and r == r_clean:
            if canonical_item is None:
                canonical_item = rel
                # 规范化首个条目的端点为字典序标准方向
                canonical_item["source"] = canon_s
                canonical_item["target"] = canon_t
            else:
                to_absorb.append(rel)
        else:
            remaining.append(rel)

    if canonical_item is not None:
        for item in to_absorb:
            merge_relation_attributes(canonical_item, item)
        remaining.append(canonical_item)

    return remaining


def merge_hierarchy_relation(relations: list, parent: str, child: str, reason: str = "") -> list:
    """
    建立层级与破除循环包含（无损合并与拓扑规整）：
    确立 parent ─[包含]▶ child 的规范单向层级，
    并将两节点之间所有的反向包含边 (child ─[包含]▶ parent)、已存在的正向包含边、
    以及低信息量粗糙相关边 (parent <-> child '相关') 的证据、来源、哈希和权重无损聚合到该规范层级边中，
    彻底消除反向包含与多余粗糙线，破除循环矛盾。
    """
    p_clean = str(parent).strip()
    c_clean = str(child).strip()
    clean_reason = str(reason).strip() if reason else ""

    if not relations:
        return [{
            "source": p_clean,
            "target": c_clean,
            "relation": "包含",
            "evidence": "AI 智能逻辑推导",
            "doc_source": "AI 分析",
            "doc_hash": "",
            "weight": 1,
            "reason": clean_reason or "建立层级分类"
        }]

    canonical_item = None
    to_absorb = []
    remaining = []

    for rel in relations:
        if not isinstance(rel, dict):
            continue
        s = str(rel.get("source", "")).strip()
        t = str(rel.get("target", "")).strip()
        r = str(rel.get("relation", "")).strip()

        is_forward = (s == p_clean and t == c_clean)
        is_reverse = (s == c_clean and t == p_clean)

        if is_forward and r == "包含":
            if canonical_item is None:
                canonical_item = rel
            else:
                to_absorb.append(rel)
        elif is_reverse and r == "包含":
            # 反向包含边：必须被吸收并消除！
            to_absorb.append(rel)
        elif (is_forward or is_reverse) and r in ["相关", "关联"]:
            # 伴随的粗糙相关边：吸收并消除
            to_absorb.append(rel)
        else:
            remaining.append(rel)

    if canonical_item is None:
        canonical_item = {
            "source": p_clean,
            "target": c_clean,
            "relation": "包含",
            "evidence": "",
            "doc_source": "",
            "doc_hash": "",
            "weight": 0,
            "reason": clean_reason
        }

    for item in to_absorb:
        merge_relation_attributes(canonical_item, item)

    # 兜底补充空缺元数据
    if not str(canonical_item.get("evidence", "")).strip():
        canonical_item["evidence"] = "AI 智能逻辑推导"
    if not str(canonical_item.get("doc_source", "")).strip():
        canonical_item["doc_source"] = "AI 分析"
    if not canonical_item.get("weight") or canonical_item.get("weight") <= 0:
        canonical_item["weight"] = 1
    if clean_reason and (not canonical_item.get("reason") or clean_reason not in str(canonical_item.get("reason"))):
        if not canonical_item.get("reason"):
            canonical_item["reason"] = clean_reason
        else:
            canonical_item["reason"] = f"{canonical_item['reason']} | {clean_reason}"

    remaining.append(canonical_item)
    return remaining


# =====================================================================
# 4. 系统总调度管道（核心：增量式累加记忆）
# =====================================================================
class BioGraphPipeline:
    def __init__(self, api_key, model="tencent/hy3-preview",base_url = "https://openrouter.ai/api/v1"):
        self.processor = PDFProcessor()
        # 把前端传进来的 model 继续传给大模型智能体
        self.agent = BioBrainAgent(api_key=api_key, model=model,base_url=base_url)
        self.visualizer = GraphVisualizer()

        # 全局图谱存储（增量更新的基础）
        self.global_entities = []  # 存储格式：[{"standard_name": "...", "aliases": [...]}]
        self.global_relations = []  # 存储格式：[{"source": "...", "target": "...", "relation": "...", "evidence": "..."}]

    def _merge_entities(self, new_entities):
        """将新抽取的实体，合并到全局实体库中（去重并合并别名）"""
        if not new_entities:
            return
        for new_ent in new_entities:
            if not isinstance(new_ent, dict):
                continue
            name = new_ent.get("standard_name")
            if not name:
                continue
            aliases = new_ent.get("aliases", [])
            if not isinstance(aliases, list):
                aliases = [aliases] if aliases else []

            # 检查全局库里是否已存在该标准实体的记录
            match = next((e for e in self.global_entities if e.get("standard_name") == name), None)
            if match:
                # 存在则合并别名并去重
                existing_aliases = match.get("aliases", [])
                match["aliases"] = list(set(existing_aliases + aliases))
            else:
                # 不存在则新增
                self.global_entities.append(new_ent)

    def _merge_relations(self, new_relations):
        """将新抽取的连线关系，合并到全局关系库中（防止完全重复的边，且强校验两端节点合法性）"""
        if not new_relations:
            return

        # 收集全局已登记的所有合法实体名（含别名）映射
        std_map = {}
        for e in self.global_entities:
            s_name = str(e.get("standard_name", "")).strip()
            if s_name:
                std_map[s_name.lower()] = s_name
                for a in e.get("aliases", []):
                    if a:
                        std_map[str(a).strip().lower()] = s_name

        valid_new = []
        for new_rel in new_relations:
            if not isinstance(new_rel, dict):
                continue
            s = new_rel.get("source")
            t = new_rel.get("target")
            r = new_rel.get("relation")
            if not s or not t:
                continue

            s_clean = str(s).strip()
            t_clean = str(t).strip()
            s_std = std_map.get(s_clean.lower())
            t_std = std_map.get(t_clean.lower())

            # 🛡️ 校验两端节点：若端点未在已登记实体库中，坚决拦截
            if not s_std or not t_std:
                print(f"   ⚠️ [关系防线] 拦截非法关系（端点未在实体字典中登记）: '{s}' -> '{t}'")
                continue

            # 规范化端点为全局标准名
            new_rel["source"] = s_std
            new_rel["target"] = t_std

            if s_std == t_std:
                continue

            valid_new.append(new_rel)

        # 核心关系规整：执行同种关系去重与对称合并（保留异类机制与相关共存，不预先自动提纯）
        all_relations = self.global_relations + valid_new
        self.global_relations = consolidate_homogeneous_relations(all_relations)

    @staticmethod
    def _is_entity_grounded_in_text(entity_name: str, text: str) -> bool:
        """使用弹性正则检查某个实体名称是否真实存在于文献原文或证据中"""
        if not entity_name or not isinstance(entity_name, str):
            return False
        clean_name = entity_name.strip()
        if len(clean_name) < 2:
            return False

        # 1. 如果是纯英文/数字/常见分子符号代号 (如 TGFBR1, p53, Smad2, CDK-4)
        if re.search(r'^[a-zA-Z0-9_\-\s/+\.\(\)]+$', clean_name):
            core_name = clean_name.strip("()[]{}").strip()
            if len(core_name) < 2:
                return False
            # 采用单词边界匹配 (前后非字母数字)
            pattern = rf"(?<![a-zA-Z0-9]){re.escape(core_name)}(?![a-zA-Z0-9])"
            if re.search(pattern, text, re.IGNORECASE):
                return True
            # 支持常见连字符变体 (如 Smad-2 vs Smad2, NF-kB vs NFkB)
            if "-" in core_name or " " in core_name:
                alt = re.sub(r'[-\s]+', '', core_name)
                alt_pattern = rf"(?<![a-zA-Z0-9]){re.escape(alt)}(?![a-zA-Z0-9])"
                if re.search(alt_pattern, text, re.IGNORECASE):
                    return True
        else:
            # 2. 中文或混合语言：子串包含检索
            if clean_name in text:
                return True

        return False

    def _ground_and_recover_chunk_hallucinations(self, chunk_text: str, ents: list, rels: list, c_source: str, enabled: bool = True):
        """
        切块结束后的终审拦截与正则文献兜底追溯器：
        - 收集该切块所有关系端点；
        - 坚决剔除任何包含生化动作伪节点（如“磷酸化”、“入核转运”）的关系；
        - 若开启兜底 (enabled=True)：对于未在初选实体字典中登记的端点，在切块原文/证据中执行弹性正则匹配；
          若原文确有其实体，则自动回填创建实体并入 ents（落实为真实节点，消除粉色幻觉！）；
          若原文完全未出现，则判定为模型虚构伪节点，安全剔除该关系；
        - 若关闭兜底 (enabled=False)：直接剔除两端未登记的关系，杜绝粉色孤岛。
        """
        if not rels:
            return ents, []

        std_map = {}
        for e in ents:
            if isinstance(e, dict):
                s_name = str(e.get("standard_name", "")).strip()
                if s_name:
                    std_map[s_name.lower()] = s_name
                    for a in e.get("aliases", []):
                        if a:
                            std_map[str(a).strip().lower()] = s_name

        recovered_entities_count = 0
        valid_relations = []

        for rel in rels:
            if not isinstance(rel, dict):
                continue
            s_raw = str(rel.get("source", "")).strip()
            t_raw = str(rel.get("target", "")).strip()
            if not s_raw or not t_raw or s_raw == t_raw:
                continue

            rel_valid = True
            endpoints_to_check = [("source", s_raw), ("target", t_raw)]

            for role, node_name in endpoints_to_check:
                node_lower = node_name.lower()
                if node_lower in std_map:
                    # 已登记实体，标准化
                    rel[role] = std_map[node_lower]
                else:
                    # 未登记端点：判断是否开启正则补漏
                    if enabled:
                        evidence = str(rel.get("evidence", ""))
                        search_scope = f"{chunk_text}\n{evidence}"
                        if self._is_entity_grounded_in_text(node_name, search_scope):
                            # 🎉 正则兜底命中！第一轮漏检的文献真实体，立刻落实回填为正规实体
                            print(f"   🔍 [正则兜底命中] 成功在文献中匹配到端点 '{node_name}'，已自动落实为真实实体！")
                            rescued_ent = {
                                "standard_name": node_name,
                                "aliases": [],
                                "category": "文献追溯实体",
                                "doc_source": c_source
                            }
                            ents.append(rescued_ent)
                            std_map[node_lower] = node_name
                            rel[role] = node_name
                            recovered_entities_count += 1
                        else:
                            # 🚫 文献无据，纯属模型幻觉捏造
                            print(f"   🛡️ [幻觉终审拦截] 端点 '{node_name}' 未在文献原文中找到任何文字支撑，已安全剔除虚构关系: '{s_raw}' -> '{t_raw}'")
                            rel_valid = False
                            break
                    else:
                        # 补漏关闭：严格丢弃未登记端点
                        print(f"   ⚠️ [未登记端点拦截] 端点 '{node_name}' 未在实体库中登记 (补漏开关已关闭)，已剔除该关系: '{s_raw}' -> '{t_raw}'")
                        rel_valid = False
                        break

            if rel_valid:
                valid_relations.append(rel)

        if recovered_entities_count > 0:
            print(f"   🧬 [切块汇总] 本切块通过正则文献兜底成功抢救落实了 {recovered_entities_count} 个漏检实体！")

        return ents, valid_relations

    def run(self, pdf_path, start_page=0, end_page=None, is_summary_only=False,use_reflection=True,source_name="未知文献",entity_lang="关闭 (保持原文语言)",output_lang="zh",progress_callback=None,concurrency=4,vision_strategy="off",vision_keyword="",vision_model=None,enable_relation_grounding=True):
        print("🚀 [Pipeline] 启动全自动化生物知识图谱构建系统...")

        current_source = os.path.basename(pdf_path)

        print(f"📌 [Pipeline] 当前处理文献来源已锁定: {current_source}")

        def report_progress(current_step, total_steps, msg):
            if progress_callback:
                progress_callback(current_step, total_steps, msg)

        is_en = "en" in output_lang.lower()

        # ---------------------------------------------------------
        # 📷 前置视觉转译流水线 (Upfront Vision Transcription)
        # ---------------------------------------------------------
        vision_chunks = []
        vision_chunk_sources = []
        if vision_strategy and vision_strategy != "off":
            print(f"👁️ [Pipeline] 启动机制图前置视觉转译 (策略: {vision_strategy}, 关键词: '{vision_keyword}')...")
            msg_vision_init = (
                f"📷 [Vision] Sniffing figures in pages {start_page + 1} to {end_page}..."
                if is_en else
                f"📷 [视觉解析] 正在检索第 {start_page + 1} 到 {end_page} 页的候选机制图..."
            )
            report_progress(0.02, 1.0, msg_vision_init)

            figures = self.processor.extract_figures(
                pdf_path,
                start_page=start_page,
                end_page=end_page,
                mode=vision_strategy,
                keyword=vision_keyword
            )

            if figures:
                msg_fig_found = (
                    f"📷 [Vision] Found {len(figures)} candidate figure(s). Transcribing mechanism text..."
                    if is_en else
                    f"📷 [视觉解析] 命中 {len(figures)} 张目标插图，正在调用视觉模型转译为学术机制文本..."
                )
                report_progress(0.05, 1.0, msg_fig_found)

                for f_idx, fig in enumerate(figures):
                    fig_label = fig.get("label", f"Fig_{f_idx+1}")
                    fig_caption = fig.get("caption", "")
                    fig_page = fig.get("page", start_page + 1)

                    text_transcription = self.agent.transcribe_figure_to_text(
                        image_bytes=fig["image_bytes"],
                        image_ext=fig.get("ext", "png"),
                        caption=fig_caption,
                        vision_model=vision_model,
                        output_lang=output_lang
                    )
                    if text_transcription and text_transcription.strip():
                        # 组装为带学术元数据的机制文本 Chunk，融入后续两阶段实体与关系抽取流
                        v_chunk = (
                            f"【文献机制通路图解析 / Visual Figure: {fig_label} (P.{fig_page})】\n"
                            f"图注说明: {fig_caption}\n"
                            f"分子调控机制与级联拓扑:\n{text_transcription}"
                        )
                        vision_chunks.append(v_chunk)
                        vision_chunk_sources.append(f"{source_name} [Figure: {fig_label} (P.{fig_page})]")
            else:
                if vision_strategy == "match" and vision_keyword:
                    print(f"ℹ️ [Pipeline] 未在选定页码中匹配到关键词 '{vision_keyword}' 的关联插图。")

        # ---------------------------------------------------------
        # 🚀 模式一：仅摘要模式 (混合双打流)
        # ---------------------------------------------------------
        if is_summary_only:
            # start_page 在前端传过来时减了1，这里加1是为了人类阅读直观
            print(f"⚡ 开启摘要模式，仅在第 {start_page + 1} 到 {end_page} 页中寻找摘要...")
            msg_init = f"⚡ [Init] Regex scanning pages {start_page + 1} to {end_page}..." if is_en else f"⚡ [初始化] 开启摘要模式，正在正则扫描第 {start_page + 1} 到 {end_page}..."
            report_progress(0.1, 1.0, msg_init)

            # 注意：这里的 raw_text 已经严格限制在了用户选定的页码范围内！
            raw_text = self.processor.get_raw_text(pdf_path, start_page, end_page)
            final_text = ""

            # 1. 第一道防线：正则捕获
            abstract_text = self.processor.extract_abstract_regex(raw_text)

            if abstract_text:
                print(f"🔍 正则成功捕获疑似摘要 (长度: {len(abstract_text)})，请求大模型质检...")
                msg_verify = "🔍 [Verifying] Regex caught potential abstract, requesting LLM content check..." if is_en else "🔍 [质检中] 正则捕获疑似摘要，请求大模型进行内容质检..."
                report_progress(0.12, 1.0, msg_verify)
                verified = self.agent.verify_and_clean_abstract(abstract_text)
                if "[NOT_ABSTRACT]" not in verified:
                    final_text = verified
                    print("✅ 质检通过，已获取高纯度摘要！")
                else:
                    print("⚠️ 大模型认为正则提取的不是有效摘要。")

            # 2. 终极兜底：让大模型在选定的页码文本 (raw_text) 中硬找
            if not final_text:
                print("⚠️ 启动大模型全量兜底搜索 (范围仅限选定页码)...")
                msg_fallback = "⚠️ [Fallback] Starting full LLM search for abstract block..." if is_en else "⚠️ [兜底搜索] 启动大模型全量兜底寻找摘要区块..."
                report_progress(0.14, 1.0, msg_fallback)
                fallback_result = self.agent.fallback_extract_abstract(raw_text)
                if "[NOT_ABSTRACT]" not in fallback_result:
                    final_text = fallback_result
                    print("✅ 兜底成功，大模型已捕获摘要！")
                else:
                    # 如果这几页里真没摘要，检查是否有视觉块
                    if not vision_chunks:
                        raise Exception("❌ 无法在指定页码中找到摘要内容，请尝试扩大页码范围，或关闭摘要模式。")
                    else:
                        print("⚠️ 未找到纯文本摘要，但捕获了机制图转译文本，将以机制图为主进行构建。")

            text_chunks = [final_text] if final_text else []

        # ---------------------------------------------------------
        # 🐢 模式二：全文解析模式 (传统的暴力分块)
        # ---------------------------------------------------------
        else:
            print(f"🐢 开启普通全文分块模式 (第 {start_page + 1} 到 {end_page} 页)...")
            text_chunks = self.processor.extract_chunks(pdf_path, start_page, end_page)

        # =========================================================
        # 融合视觉块与文本块，构建统一分析输入流
        # =========================================================
        chunks = vision_chunks + text_chunks
        chunk_sources = vision_chunk_sources + [source_name] * len(text_chunks)
        total_chunks = len(chunks)

        if not chunks:
            return self.global_entities, self.global_relations

        # =============================================================
        # 🚀 切块级局部高纯度闭环提取流水线 (Chunk-Centric Localized Pipeline)
        # 彻底解决两阶段全局大字典污染导致的幻觉激增问题！
        # 每个切块独立提取本地实体，并严格仅基于本地实体推演该切块的关系
        # =============================================================
        default_reason = "No detailed explanation" if is_en else "无详细解释"
        source_prefix = "Source" if is_en else "源自"
        worker_count = max(1, min(int(concurrency), total_chunks))

        def _process_single_chunk(idx, chunk_text, c_source):
            """单个切块的自给自足闭环处理函数"""
            try:
                # 1. 块内精准实体提取与反思
                ents = self.agent.extract_entities_with_reflection(
                    chunk_text, use_reflection=use_reflection, entity_lang=entity_lang
                )
                if not isinstance(ents, list):
                    ents = []

                for ent in ents:
                    if isinstance(ent, dict):
                        ent["doc_source"] = c_source

                # 2. 紧扣当前切块本地实体的闭环关系抽取 (绝无跨切块全局无关大字典污染！)
                rels = []
                if ents:
                    rels = self.agent.extract_relations(chunk_text, ents)
                    if not isinstance(rels, list):
                        rels = []

                    source_tag = c_source if c_source != source_name else current_source
                    for rel in rels:
                        if isinstance(rel, dict):
                            rel["doc_source"] = c_source
                            original_reason = rel.get("reason", default_reason)
                            rel["reason"] = f"{original_reason} [{source_prefix}: {source_tag}]"

                # 3. 🔍 切块结束后的终审拦截与正则文献兜底追溯落实
                ents, rels = self._ground_and_recover_chunk_hallucinations(
                    chunk_text=chunk_text,
                    ents=ents,
                    rels=rels,
                    c_source=c_source,
                    enabled=enable_relation_grounding
                )

                return idx, ents, rels, None
            except Exception as exc:
                return idx, [], [], exc

        raw_chunk_results = [([], []) for _ in range(total_chunks)]

        if total_chunks == 1 or worker_count == 1:
            # 单块或串行模式：直观顺畅推进
            for idx in range(total_chunks):
                chunk = chunks[idx]
                c_source = chunk_sources[idx]
                msg = (
                    f"🧠 [Chunk {idx + 1}/{total_chunks}] Extracting local entities & relations..."
                    if is_en else
                    f"🧠 [文本切块 {idx + 1}/{total_chunks}] 正在闭环推演局部实体与调控关系..."
                )
                report_progress(0.2 + 0.7 * (idx / total_chunks), 1.0, msg)
                _, ents, rels, err = _process_single_chunk(idx, chunk, c_source)
                if err:
                    print(f"⚠️ [Chunk {idx + 1}] 处理遇到异常 (已跳过): {err}")
                raw_chunk_results[idx] = (ents, rels)
        else:
            # 多切块并发模式：每个 Worker 独立走完本地切块的实体+关系闭环，无两阶段屏障阻塞！
            print(f"🚀 [Pipeline 并发引擎] 启动切块局部闭环并发流水线: 切块总数={total_chunks}, 并发线程数={worker_count}")
            completed_chunks = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = {
                    executor.submit(_process_single_chunk, i, chunks[i], chunk_sources[i]): i
                    for i in range(total_chunks)
                }
                for fut in concurrent.futures.as_completed(futures):
                    idx, ents, rels, err = fut.result()
                    if err:
                        print(f"⚠️ [Chunk {idx + 1}] 并发处理遇到异常 (已跳过): {err}")
                    raw_chunk_results[idx] = (ents, rels)
                    completed_chunks += 1

                    progress = 0.15 + 0.80 * (completed_chunks / total_chunks)
                    msg = (
                        f"⚡ [Progress {completed_chunks}/{total_chunks}] Chunk {idx + 1} analyzed..."
                        if is_en else
                        f"⚡ [并发进度 {completed_chunks}/{total_chunks}] 切块 {idx + 1} 分析完成..."
                    )
                    report_progress(progress, 1.0, msg)

        # 汇总阶段：主线程统一安全归并至全局实体库与关系库
        for idx in range(total_chunks):
            ents, rels = raw_chunk_results[idx]
            self._merge_entities(ents)
            self._merge_relations(rels)

        print(f"\n📊 [Pipeline] 分析完毕！全局共捕获 {len(self.global_entities)} 个标准实体，{len(self.global_relations)} 条调控关系。")

        msg_done = (
            f"✨ Analysis complete! Caught {len(self.global_entities)} entities, {len(self.global_relations)} relations."
            if is_en else
            f"✨ 分析完毕！本轮共捕获 {len(self.global_entities)} 个实体，{len(self.global_relations)} 条关系。"
        )
        report_progress(1.0, 1.0, msg_done)
        return self.global_entities, self.global_relations


# =====================================================================
# 🧠 图谱挖掘引擎：负责在已有知识图谱中寻找拓扑路径
# =====================================================================
class GraphMiner:
    @staticmethod
    def find_paths(relations, start_node, end_node, max_depth=4, exclude_shortcuts=True):
        """
        无向图 BFS（广度优先搜索）算法：寻找两个节点之间的所有路径
        :param relations: 全局关系字典列表
        :param start_node: 起点名称
        :param end_node: 终点名称
        :param max_depth: 最大搜索深度
        :param exclude_shortcuts: 💡 是否屏蔽被洗树功能降级的捷径边（默认 True，逼迫算法寻找深层机制）
        :return: list of paths
        """
        # 1. 构建双向邻接表 (Adjacency List)
        adj = collections.defaultdict(list)
        for rel in relations:
            # 🛡️ 核心屏蔽网：如果是捷径边，直接当它不存在！
            if exclude_shortcuts and rel.get("is_shortcut", False):
                continue

            src = rel.get("source", "").strip()
            tgt = rel.get("target", "").strip()
            if not src or not tgt:
                continue

            # 正向边
            adj[src].append((tgt, rel))
            # 反向边 (无向化处理)
            adj[tgt].append((src, rel))

        # 2. 广度优先搜索 (BFS) 寻找所有路径
        queue = collections.deque([(start_node, [], {start_node})])
        valid_paths = []

        while queue:
            current, path, visited = queue.popleft()

            # 触达终点，保存路径
            if current == end_node and len(path) > 0:
                valid_paths.append(path)
                continue

            # 超过最大步数限制，不再往下钻取
            if len(path) >= max_depth:
                continue

            # 遍历当前节点的所有邻居
            for neighbor, edge in adj[current]:
                if neighbor not in visited:
                    new_visited = set(visited)
                    new_visited.add(neighbor)
                    new_path = list(path)
                    new_path.append(edge)

                    queue.append((neighbor, new_path, new_visited))

        # 3. 按路径长度（步数）从小到大排序返回
        valid_paths.sort(key=len)
        return valid_paths

# =====================================================================
# ⚙️ 启动入口
# =====================================================================
if __name__ == "__main__":
    MY_API_KEY = ""
    PDF_FILE = "sample_paper.pdf"  # 请确保这个文件存在

    if os.path.exists(PDF_FILE):
        pipeline = BioGraphPipeline(api_key=MY_API_KEY)
        pipeline.run(PDF_FILE)
    else:
        print(f"❌ 错误：未能在当前目录下找到测试文件 '{PDF_FILE}'，请放置一个PDF并重命名后再试。")