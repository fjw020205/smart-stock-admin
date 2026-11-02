export function flattenMenus(tree, output = []) {
  for (const item of tree || []) {
    output.push(item)
    if (item.children?.length) flattenMenus(item.children, output)
  }
  return output
}

export function firstLeaf(tree) {
  for (const item of tree || []) {
    if (item.children?.length) {
      const found = firstLeaf(item.children)
      if (found) return found
    } else if (item.permission) {
      return item
    }
  }
  return null
}
