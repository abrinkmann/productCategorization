import torch


class CategoryDatasetRNN(torch.utils.data.Dataset):
    def __init__(self, texts, labels, tokenizer, encoder):
        # Preprocess encodings
        self.encodings = tokenizer(texts, padding=True, truncation=True)

        # Preprocess labels
        self.labels = [encoder.get(x)['derived_path'] for x in labels]


    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]).to(torch.int64) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx]).to(torch.int64)
        return item

    def __len__(self):
        return len(self.labels)
