class RestrictionAdapter:
    """
    A class to handle restrictions from challenge descriptions.
    """
    @staticmethod
    def get_restrictions(desc: str) -> dict[str, list[str]]:
        """
        Extracts restrictions from a challenge description.
        
        :param desc: The challenge description containing placeholders.
        :return: A dictionary with players as keys and their restrictions as values.
        """
        if not desc:
            return {}
        try:
            restrictions = {}
            restr_list = [part[1:-1] for part in desc.split(' ') if part.startswith('{') and part.endswith('}')]
            for restr in restr_list:
                parts = restr.split(':')
                player = parts[0]
                restrictions[player.replace(' ', '')] = [r.replace(' ', '') for r in parts[1:]] if len(parts) > 1 else []
            return restrictions
        except Exception as e:
            print(f"Error extracting restrictions: {e}")
            return {}
        
    @staticmethod
    def get_num_participants(desc: str) -> int:
        if not desc:
            return 0
        try:
            restrictions = RestrictionAdapter.get_restrictions(desc)
            return len(restrictions)

        except Exception as e:
            print(f"Error counting group participants: {e}")

    @staticmethod
    def get_num_males(desc: str) -> int:
        if not desc:
            return 0
        try:
            restrictions = RestrictionAdapter.get_restrictions(desc)
            return sum(1 for restrs in restrictions.values() if restrs and 'gender=male' in restrs)

        except Exception as e:
            print(f"Error counting males: {e}")

    @staticmethod
    def get_num_females(desc: str) -> int:
        if not desc:
            return 0
        try:
            restrictions = RestrictionAdapter.get_restrictions(desc)
            return sum(1 for restrs in restrictions.values() if restrs and 'gender=female' in restrs)

        except Exception as e:
            print(f"Error counting females: {e}")