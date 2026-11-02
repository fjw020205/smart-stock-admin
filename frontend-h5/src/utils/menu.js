export function flattenMenus(tree, output = []) {
  for (const item of tree || []) {
    output.push(item)
    if (item.children?.length) flattenMenus(item.children, output)
  }
  return output
}
