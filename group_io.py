import bpy

def debug_print(*args):
    print(*args)
    pass


def export_attrs(input, *excludes):
    return {attr: to_val(getattr(input, attr)) for attr in dir(input) if valid_attr(input, attr, excludes)}


def export_node(node):
    obj = {
            'bl_idname': node.bl_idname,
            'type': node.type,
            'attr': export_attrs(node, 'node_tree', 'parent'),
            'inputs': [export_attrs(ip) for ip in node.inputs],
            'outputs': [export_attrs(op) for op in node.outputs],
    }
    if node.type == 'GROUP':
        obj['GROUP_NAME'] = node.node_tree.name
    return obj


def export_link(nodes, link):
    return {
        'from_node': nodes.index(link.from_node),
        'from_socket': list(link.from_node.outputs).index(link.from_socket),
        'to_node': nodes.index(link.to_node),
        'to_socket': list(link.to_node.inputs).index(link.to_socket)
    }


def valid_attr(obj, attr, excludes):
    if attr in excludes:
        return False

    if attr.startswith("__"):
        return False

    val = getattr(obj, attr)
    valid = None
    try:
        setattr(obj, attr, val)
        return True
    except:
        return False


def to_val(val):
    if isinstance(val, str) or isinstance(val, int) or isinstance(val, float) or isinstance(val, bool) or val == None:
        return val
    else:
        return list(val)

def export_group(grp):
    return {
            'name': grp.node_tree.name,
            'bl_idname': grp.node_tree.bl_idname,
            'nodes': [export_node(node) for node in grp.node_tree.nodes],
            'links': [export_link(list(grp.node_tree.nodes), link) for link in grp.node_tree.links],
            'tree_attr': export_attrs(grp.node_tree, 'active_output', 'active_input', 'use_fake_user'),
            'inputs': [export_attrs(ip) for ip in grp.node_tree.inputs],
            'outputs': [export_attrs(op) for op in grp.node_tree.outputs],
    }


def export_groups(node_groups):
    return [export_group(grp) for grp in reversed(node_groups)]


def import_g(inputs, n):
    for x in inputs:
        print(x)
        inputs.remove(x)
    debug_print('group', inputs, len(inputs), len(n))
    for src in n:
        debug_print('in', src)
        if 'bl_socket_idname' in src:
            t = src['bl_socket_idname']
        elif 'bl_idname' in src:
            t = src['bl_idname']
        dst = inputs.new(name=src['name'], type=t)
        #if t!='NodeSocketVirtual' and 'NodeSocketVirtual' in str(dst):
        #    raise Exception('NodeSocketVirtual')
        #if dst.bl_idname!=src['bl_idname']:
        #    raise Exception('different bl_idname: ' + dst.bl_idname)
        for k, v in src.items():
            if k=='name' or k=='bl_idname':
                continue
            debug_print('    ', inputs, dst, k, v)
            setattr(dst, k, v)

'''
def import_output(outputs, n):
    for x in outputs:
        print('remove', x)
        outputs.remove(x)
    debug_print('out', outputs, len(outputs), len(n))
    for src in n:
        debug_print('out', src)
        dst = outputs.new(name=src['name'], type=src['bl_idname'])
        if src['bl_idname']!='NodeSocketVirtual' and 'NodeSocketVirtual' in str(dst):
            raise Exception('NodeSocketVirtual')
        if dst.bl_idname!=src['bl_idname']:
            raise Exception('different bl_idname: ' + dst.bl_idname)
        for k, v in src.items():
            if k=='name' or k=='bl_idname':
                continue
            debug_print('    ', outputs, dst, k, v)
            setattr(dst, k, v)
'''

def import_inout(node, n):
    debug_print('inout', node)
    if len(node.inputs)!=len(n['inputs']):
            raise Exception()
    for dst, src in zip(node.inputs, n['inputs']):
        for k, v in src.items():
            #debug_print('    ', node, dst, k, v)
            setattr(dst, k, v)

    if len(node.outputs)!=len(n['outputs']):
            raise Exception()
    for dst, src in zip(node.outputs, n['outputs']):
        for k, v in src.items():
            #debug_print('    ', node, dst, k, v)
            setattr(dst, k, v)

def import_groups(src):
    groups = {}
    for g in src:
        #
        # group
        #
        if g['bl_idname']!='ShaderNodeTree':
            raise Exception('not ShaderNodeTree')
        group = bpy.data.node_groups.new(g['name'], g['bl_idname'])
        print(group)

        group.use_fake_user = True
        groups[g['name']] = group

        print('## tree_attr')
        for k, v in g['tree_attr'].items():
            if k=='name' or k=='bl_idname':
                continue
            print(group, k, v)
            setattr(group, k, v)

        print('## tree in out')
        import_g(group.inputs, g['inputs'])
        import_g(group.outputs, g['outputs'])

        print('## nodes')
        nodes = []
        for n in g['nodes']:
            node = group.nodes.new(n['bl_idname'])
            if 'GROUP_NAME' in n:
                node.node_tree = groups[n['GROUP_NAME']]
            nodes.append(node)

            import_inout(node, n)

            for k, v in n['attr'].items():
                setattr(node, k, v)


        print('## links: %d' % len(nodes))
        for l in g['links']:
            print(l)
            from_node = nodes[l['from_node']]
            print(from_node, len(from_node.inputs), len(from_node.outputs))
            to_node = nodes[l['to_node']]
            print(to_node, len(to_node.inputs), len(to_node.outputs))
            from_socket = from_node.outputs[l['from_socket']]
            to_socket = to_node.inputs[l['to_socket']]
            group.links.new(from_socket, to_socket, verify_limits=False)
    return groups


if __name__ == '__main__':
    print('####')
    size = 0.0
    main_area = None
    for area in bpy.context.screen.areas:
        if area.type == 'NODE_EDITOR' and area.width * area.height > size:
            size = area.width * area.height
            main_area = area
    active_group = main_area.spaces[0].node_tree.nodes.active

    groups = [active_group]
    index = 0
    while len(groups) > index:
        for node in groups[index].node_tree.nodes:
            if node.type == 'GROUP':
                groups.append(node)
            index += 1

    remove = []
    for i in range(0, len(groups)):
        grp1 = groups[i]
        for j in range(i+1, len(groups)):
            grp2 = groups[j]
            if grp1 != grp2 and grp1.node_tree == grp2.node_tree:
                remove.append(grp1)
    for x in remove:
        groups.remove(x)

    exported = export_groups(groups)

    import_groups(exported)

    #print(repr(exported))

    #import json
    #print(json.dumps(exported, indent=2))

