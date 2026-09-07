class ReadOnlyModel(dict):
    """
    Like a SQLAlchemy model, but for faster read and no modification.
    """

    __getattr__ = dict.__getitem__

    def __setattr__(self, name, value):
        raise Exception("read-only model")

    def __delattr__(self, name):
        raise Exception("read-only model")

    def to_dict(self):
        return self

    def __hash__(self):
        return id(self)

    __eq__ = dict.__eq__
