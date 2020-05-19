from haystack import indexes
from port.models import Port


class PortIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.NgramField(model_attr='name')
    name_l = indexes.IntegerField()
    maintainers = indexes.MultiValueField()
    description = indexes.EdgeNgramField(model_attr='description')
    variants = indexes.MultiValueField()
    active = indexes.BooleanField(model_attr='active')

    def get_model(self):
        return Port

    def prepare_name_l(self, obj):
        return len(obj.name)

    def prepare_maintainers(self, obj):
        return [m.github for m in obj.maintainers.all()]

    def prepare_variants(self, obj):
        return [v.variant for v in obj.variants.all()]
