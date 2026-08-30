Hairline table, muted 12px header, no zebra stripes. Use `render` for Delta cells or ticker cells.

```jsx
<DataTable columns={[{key:"stock",label:"Stock"},{key:"change",label:"Change %",render:r=><Delta value={r.change}/>}]} rows={data} />
```
