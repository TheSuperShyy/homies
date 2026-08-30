The base surface. `title` + `action` render the standard header row. Use `nested` for tiles inside a card (ticker tiles inside "My Portfolio").

```jsx
<Card title="Portfolio Performance" action={<Button variant="secondary" size="sm">See all</Button>}>…</Card>
<Card nested padding={14}>…</Card>
```
